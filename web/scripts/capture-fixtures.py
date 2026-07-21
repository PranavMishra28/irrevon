"""Capture the canonical workbench fixture set from the REAL engine.

Runs the implemented engine (src/detent at the current rc/v0.1 commit) against
its reference C2 destination and a scratch Postgres database, drives a spread
of scenarios (clean settle, lost response + reconcile, rejected dispatch,
destination-internal duplicate, unresolved ambiguity, orphan sweep, and the
re-synthesis denial), then writes:

  web/fixtures/canonical/effects.json       Q1 envelope of EffectRecord exchange shapes
  web/fixtures/canonical/findings.json      Q2 envelope of ReconciliationFinding shapes
  web/fixtures/canonical/inspect/<id>.json  verbatim `detent inspect --json` payloads
  web/fixtures/canonical/health.json        verbatim `detent doctor --json` payload
  web/fixtures/canonical/adapters.json      the real capability declaration(s)
  web/fixtures/canonical/demo-artifact.json events + summary of `detent demo --seed 777`
  web/fixtures/canonical/provenance.json    commit, seed, commands, generated-at
  web/fixtures/manifest.sha256              content hashes (drift-gated in CI)

Every exchange-shaped record is validated against schemas/*.schema.json before
being written. No field is invented: everything is read from the ledger the
real run produced, except the Q1/Q2 envelope framing ratified in RFC-002 §9
and resolution evidence digests, which are RFC 8785 canonical digests of the
stored resolution evidence (derivation noted in provenance.json).

Usage (from the repo root, with the engine venv):
  DETENT_LEDGER_PASSWORD=... .venv/bin/python web/scripts/capture-fixtures.py \
      --dsn postgresql://detent@localhost:5544/detent --seed 777
"""

from __future__ import annotations

import argparse
import contextlib
import hashlib
import io
import json
import subprocess
import sys
import time
import urllib.request
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

import psycopg
import rfc8785
from jsonschema import Draft202012Validator
from psycopg import sql
from psycopg.rows import dict_row

WEB = Path(__file__).resolve().parent.parent
REPO = WEB.parent
OUT = WEB / "fixtures" / "canonical"
SCHEMAS = REPO / "schemas"

sys.path.insert(0, str(REPO / "src"))

from detent.adapters.base import declarations_dir, load_declaration  # noqa: E402
from detent.api import Engine  # noqa: E402
from detent.cli.inspect_cmd import run_inspect  # noqa: E402
from detent.ledger.db import apply_migrations  # noqa: E402
from detent.reconciler import ReconcileConfig  # noqa: E402


def iso(dt: Any) -> str:
    if isinstance(dt, datetime):
        return dt.astimezone(UTC).isoformat().replace("+00:00", "Z")
    return str(dt)


def validator(name: str) -> Draft202012Validator:
    schema = json.loads((SCHEMAS / f"{name}.schema.json").read_text())
    return Draft202012Validator(schema)


def contract(
    stable_ids: dict[str, str],
    effect_type: str,
    scope: str,
    parameters: dict[str, Any],
    authority_ref: str,
    effect_class: str = "IRREVERSIBLE",
) -> dict[str, Any]:
    return {
        "schema_version": "1",
        "stable_ids": stable_ids,
        "effect_type": effect_type,
        "effect_class": effect_class,
        "scope": scope,
        "adapter_id": "refdest-c2",
        "parameters": parameters,
        "authority_ref": authority_ref,
        "stamped_at": iso(datetime.now(UTC)),
    }


def control(base_url: str, path: str, body: dict[str, Any] | None = None) -> Any:
    if body is None:
        with urllib.request.urlopen(f"{base_url}{path}", timeout=10) as resp:
            return json.loads(resp.read())
    req = urllib.request.Request(
        f"{base_url}{path}",
        data=json.dumps(body).encode(),
        headers={"Content-Type": "application/json"},
        method="POST",
    )
    with urllib.request.urlopen(req, timeout=10) as resp:
        return json.loads(resp.read())


def schedule(base_url: str, entries: list[dict[str, Any]]) -> None:
    control(base_url, "/control/schedule", {"entries": entries})


RESYNTHESIZED = {
    "items": [{"sku": "SKU-118", "qty": 2, "gift_wrap": False}],
    "shipping": {"method": "standard", "priority": "normal"},
    "customer_note": "Deliver at loading dock please!",
}


def run_scenarios(engine: Engine, base_url: str) -> dict[str, str]:
    """Returns {label: effect_id}. Every state below is produced by the real
    engine + destination, never written directly."""
    ids: dict[str, str] = {}

    # S1 — flagship: response lost after commit → AMBIGUOUS → reconcile →
    # SETTLED_COMMITTED + CONFIRMED_UNIQUE (auto-closed) → re-synthesized retry
    # collapses to the same effect and the gate denies with cited evidence.
    c1 = contract(
        {"order_id": "9410", "customer_ref": "C-0007"},
        "order.create",
        "acme-store/prod",
        {
            "line_items": [{"sku": "SKU-118", "quantity": 2}],
            "shipping_method": "standard",
            "note": "please deliver to the loading dock",
        },
        "auth_approved_task_18",
    )
    reg = engine.register_intent(c1)
    ids["flagship"] = reg.effect_id
    schedule(base_url, [{"match": {"op": "create"}, "fault": "DROP_RESPONSE_AFTER_COMMIT"}])
    engine.dispatch(reg.effect_id)
    schedule(base_url, [])
    engine.reconcile(reg.effect_id)
    engine.register_intent(
        contract(
            {"order_id": "9410", "customer_ref": "C-0007"},
            "order.create",
            "acme-store/prod",
            RESYNTHESIZED,
            "auth_approved_task_22",
        )
    )
    engine.dispatch(reg.effect_id)  # gate DENY (dedup) with evidence

    # S2 — clean OK settle; no reconciliation touched it → UNRECONCILED.
    reg2 = engine.register_intent(
        contract(
            {"invoice_id": "INV-2201"},
            "refund.create",
            "acme-store/prod",
            {"amount_minor": 4599, "currency": "EUR", "reason": "damaged in transit"},
            "auth_approved_task_31",
            effect_class="COMPENSABLE",
        )
    )
    ids["clean-settle"] = reg2.effect_id
    engine.dispatch(reg2.effect_id)

    # S3 — recognized, declaration-cited rejection → SETTLED_FAILED (TERMINAL).
    reg3 = engine.register_intent(
        contract(
            {"shipment_id": "SHP-88121"},
            "shipment.create",
            "acme-logistics/prod",
            {"reject": True, "carrier": "postal", "weight_g": 1200},
            "auth_approved_task_44",
            effect_class="COMPENSABLE",
        )
    )
    ids["rejected"] = reg3.effect_id
    engine.dispatch(reg3.effect_id)

    # S4 — lost before commit → AMBIGUOUS → reconcile → confirmed absent →
    # SETTLED_FAILED + LOST finding (stays OPEN: real open work for Attention).
    reg4 = engine.register_intent(
        contract(
            {"notification_id": "NTF-501", "workflow_command_id": "wf_cmd_00088"},
            "notification.send",
            "acme-store/prod",
            {"channel": "email", "template": "order-shipped"},
            "auth_approved_task_47",
            effect_class="IDEMPOTENT",
        )
    )
    ids["lost"] = reg4.effect_id
    schedule(
        base_url, [{"match": {"op": "create"}, "fault": "DROP_RESPONSE_BEFORE_COMMIT"}]
    )
    engine.dispatch(reg4.effect_id)
    schedule(base_url, [])
    engine.reconcile(reg4.effect_id)

    # S5 — destination-internal duplication (refdest-only fault) → OK settle,
    # then audit read-back shows n=2 → DUPLICATE finding with excess count.
    reg5 = engine.register_intent(
        contract(
            {"order_id": "9411", "customer_ref": "C-0019"},
            "order.create",
            "acme-store/prod",
            {"line_items": [{"sku": "SKU-9", "quantity": 1}]},
            "auth_approved_task_52",
        )
    )
    ids["duplicate"] = reg5.effect_id
    schedule(base_url, [{"match": {"op": "create"}, "fault": "DUPLICATE_ACCEPT"}])
    engine.dispatch(reg5.effect_id)
    schedule(base_url, [])
    engine.audit(reg5.effect_id)

    # S6 — registered, never dispatched → PERSISTED.
    reg6 = engine.register_intent(
        contract(
            {"payout_id": "PO-3307"},
            "payout.create",
            "acme-finance/prod",
            {"amount_minor": 125000, "currency": "EUR"},
            "auth_approved_task_61",
        )
    )
    ids["persisted"] = reg6.effect_id

    # S7 — response lost, NOT yet reconciled → parked AMBIGUOUS (open doubt).
    reg7 = engine.register_intent(
        contract(
            {"subscription_id": "SUB-77", "workflow_command_id": "wf_cmd_00104"},
            "subscription.cancel",
            "acme-store/prod",
            {"effective": "period-end"},
            "auth_approved_task_63",
            effect_class="REVERSIBLE",
        )
    )
    ids["ambiguous-open"] = reg7.effect_id
    schedule(base_url, [{"match": {"op": "create"}, "fault": "DROP_RESPONSE_AFTER_COMMIT"}])
    engine.dispatch(reg7.effect_id)
    schedule(base_url, [])

    # S8 — an out-of-band destination effect nothing in the ledger intended;
    # two sweep passes (orphan confirmation needs a re-sighting) → ORPHANED.
    control(
        base_url,
        "/control/oob",
        {"effect_type": "order.create", "payload": {"source": "legacy-batch-import"}},
    )
    window_from = "2026-01-01T00:00:00Z"
    window_to = "2026-12-31T23:59:59Z"
    engine.sweep("refdest-c2", window_from, window_to)
    time.sleep(0.05)
    engine.sweep("refdest-c2", window_from, window_to)

    return ids


def effect_record_exchange(conn: psycopg.Connection[dict[str, Any]], effect_id: str) -> dict[str, Any]:
    rec = conn.execute(
        "SELECT * FROM effect_records WHERE effect_id = %s", (effect_id,)
    ).fetchone()
    assert rec is not None
    frontier = conn.execute(
        """
        SELECT f.frontier, e.operation_id, e.step
        FROM effect_frontiers f
        JOIN effect_executions e ON e.effect_id = f.effect_id
        WHERE f.effect_id = %s
        ORDER BY e.step DESC LIMIT 1
        """,
        (effect_id,),
    ).fetchone()
    assert frontier is not None
    lifecycle_at = conn.execute(
        """
        SELECT t.created_at FROM effect_transitions t
        JOIN effect_executions e USING (execution_id)
        WHERE e.effect_id = %s ORDER BY t.transition_seq DESC LIMIT 1
        """,
        (effect_id,),
    ).fetchone()
    assert lifecycle_at is not None
    # Authority linkage lives in the authorities adjunct tables (RFC-002 §2.2).
    authority = conn.execute(
        """
        SELECT a.authority_ref, a.stamped_at
        FROM effect_authorities ea JOIN authorities a USING (authority_id)
        WHERE ea.effect_id = %s ORDER BY ea.link_id LIMIT 1
        """,
        (effect_id,),
    ).fetchone()
    assert authority is not None
    out: dict[str, Any] = {
        "schema_version": "1",
        "effect_id": rec["effect_id"],
        "operation_id": frontier["operation_id"],
        "step": frontier["step"],
        "effect_type": rec["effect_type"],
        "effect_class": rec["effect_class"],
        "scope": rec["scope"],
        "stable_ids": dict(rec["stable_ids"]),
        "adapter_id": rec["adapter_id"],
        "declaration_digest": rec["declaration_digest"],
        "parameters_digest": rec["parameters_digest"],
        "authority_ref": authority["authority_ref"],
        "stamped_at": iso(authority["stamped_at"]),
        "lifecycle": frontier["frontier"],
        "lifecycle_at": iso(lifecycle_at["created_at"]),
        "created_at": iso(rec["created_at"]),
    }
    if rec["branch_ref"] is not None:
        out["branch_ref"] = rec["branch_ref"]
    if rec["event_time"] is not None:
        out["event_time"] = iso(rec["event_time"])
    return out


def finding_exchange(
    conn: psycopg.Connection[dict[str, Any]], row: dict[str, Any]
) -> dict[str, Any]:
    resolutions = conn.execute(
        """
        SELECT * FROM finding_resolutions WHERE finding_id = %s
        ORDER BY resolution_seq
        """,
        (row["finding_id"],),
    ).fetchall()
    if resolutions:
        last = resolutions[-1]
        resolution: dict[str, Any] = {"status": last["to_status"]}
        if last["to_status"] != "OPEN":
            # RFC 8785 canonical digest of the stored resolution evidence —
            # a mechanical derivation of real ledger bytes (see provenance).
            digest = hashlib.sha256(rfc8785.dumps(last["evidence"])).hexdigest()
            resolution["evidence_digest"] = f"sha256:{digest}"
            resolution["resolved_at"] = iso(last["created_at"])
    else:
        resolution = {"status": "OPEN"}

    subject: dict[str, Any]
    if row["classification"] == "ORPHANED":
        subject = {
            "adapter_id": row["adapter_id"],
            "destination_ref": row["destination_ref"],
        }
    else:
        subject = {"effect_id": row["effect_id"]}

    out: dict[str, Any] = {
        "schema_version": "1",
        "finding_id": f"fnd_{row['finding_id']:020d}",
        "subject": subject,
        "adapter_id": row["adapter_id"],
        "classification": row["classification"],
        "evidence_digest": row["evidence_digest"],
        "evidence": {"digest": row["evidence_digest"], "bundle": None, "redaction": "digest_only"},
        "created_by": row["created_by"],
        "created_at": iso(row["created_at"]),
        "resolution": resolution,
    }
    if row["classification"] == "DUPLICATE":
        out["excess_effect_count"] = row["excess_effect_count"]
    return out


def capture_inspect(dsn: str, effect_id: str) -> dict[str, Any]:
    buf = io.StringIO()
    with contextlib.redirect_stdout(buf):
        code = run_inspect(dsn, effect_id, reveal=False, as_json=True)
    if code not in (0,):
        raise RuntimeError(f"inspect exited {code} for {effect_id}")
    loaded = json.loads(buf.getvalue())
    assert isinstance(loaded, dict)
    return loaded


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--dsn", required=True, help="admin DSN (password via env)")
    parser.add_argument("--seed", type=int, default=777)
    parser.add_argument("--demo-jsonl", default=None,
                        help="path to a captured `detent demo --jsonl` transcript")
    parser.add_argument("--doctor-json", default=None,
                        help="path to a captured `detent doctor --json` payload")
    parser.add_argument("--flagship-dsn", default=None,
                        help="kept demo database (detent_demo_s<seed>); when given, "
                             "the flagship effect's record + inspect are sourced from "
                             "the REAL crash-and-recovery run instead of the in-process rerun")
    args = parser.parse_args()

    fixture_db = f"detent_wbfix_s{args.seed}"
    with psycopg.connect(args.dsn, autocommit=True) as admin:
        admin.execute(
            sql.SQL("DROP DATABASE IF EXISTS {}").format(sql.Identifier(fixture_db))
        )
        admin.execute(sql.SQL("CREATE DATABASE {}").format(sql.Identifier(fixture_db)))
    dsn = psycopg.conninfo.make_conninfo(args.dsn, dbname=fixture_db)
    apply_migrations(dsn)

    refdest = subprocess.Popen(
        [sys.executable, "-m", "detent.adapters.refdest_server", "--port", "0",
         "--seed", str(args.seed)],
        stdout=subprocess.PIPE,
        stderr=subprocess.DEVNULL,
        text=True,
    )
    assert refdest.stdout is not None
    base_url = f"http://127.0.0.1:{int(refdest.stdout.readline().strip().rsplit(' ', 1)[1])}"

    declaration = load_declaration(declarations_dir() / "refdest-c2.capability.json")
    from detent.adapters.refdest import RefdestAdapter

    adapter = RefdestAdapter("refdest-c2", declaration, base_url=base_url)
    try:
        engine = Engine(
            dsn,
            {"refdest-c2": adapter},
            reconcile_config=ReconcileConfig(absence_reread_gap_s=0.0, probe_deadline_s=5.0),
        )
        engine.boot()
        ids = run_scenarios(engine, base_url)
        engine.close()

        rec_validator = validator("effect-record")
        fnd_validator = validator("reconciliation-finding")
        cap_validator = validator("capability-declaration")

        with psycopg.connect(dsn, row_factory=dict_row) as conn:
            records = []
            for label, effect_id in ids.items():
                if label == "flagship" and args.flagship_dsn:
                    with psycopg.connect(
                        args.flagship_dsn, row_factory=dict_row
                    ) as demo_conn:
                        record = effect_record_exchange(demo_conn, effect_id)
                else:
                    record = effect_record_exchange(conn, effect_id)
                rec_validator.validate(record)
                records.append(record)
            records.sort(key=lambda r: r["created_at"], reverse=True)

            finding_rows = conn.execute(
                "SELECT * FROM findings ORDER BY finding_id"
            ).fetchall()
            findings = []
            for row in finding_rows:
                finding = finding_exchange(conn, row)
                fnd_validator.validate(finding)
                findings.append(finding)

        as_of = iso(datetime.now(UTC))
        OUT.mkdir(parents=True, exist_ok=True)
        (OUT / "inspect").mkdir(exist_ok=True)

        effects_envelope = {
            "schema_version": "1",
            "data": records,
            "has_more": False,
            "next_cursor": None,
            "as_of": as_of,
        }
        findings_envelope = {
            "schema_version": "1",
            "data": findings,
            "has_more": False,
            "next_cursor": None,
            "as_of": as_of,
        }

        inspects: dict[str, dict[str, Any]] = {}
        for label, effect_id in ids.items():
            source_dsn = (
                args.flagship_dsn if label == "flagship" and args.flagship_dsn else dsn
            )
            inspects[effect_id] = capture_inspect(source_dsn, effect_id)

        cap = json.loads(
            (declarations_dir() / "refdest-c2.capability.json").read_text()
        )
        cap_validator.validate(cap)
        adapters_payload = {"schema_version": "1", "data": [cap], "as_of": as_of}

        files: dict[str, Any] = {
            "effects.json": effects_envelope,
            "findings.json": findings_envelope,
            "adapters.json": adapters_payload,
        }
        for effect_id, payload in inspects.items():
            files[f"inspect/{effect_id}.json"] = payload
        if args.demo_jsonl:
            lines = [
                json.loads(line)
                for line in Path(args.demo_jsonl).read_text().splitlines()
                if line.strip()
            ]
            files["demo-artifact.json"] = {
                "schema_version": "1",
                "events": lines[:-1],
                "summary": lines[-1],
            }
        if args.doctor_json:
            files["health.json"] = json.loads(Path(args.doctor_json).read_text())

        commit = subprocess.run(
            ["git", "-C", str(REPO), "rev-parse", "HEAD"],
            capture_output=True, text=True, check=True,
        ).stdout.strip()
        files["provenance.json"] = {
            "generated_at": as_of,
            "engine_commit": commit,
            "seed": args.seed,
            "source": "real engine run (src/detent) against the refdest-c2 reference destination",
            "notes": [
                "effects.json/findings.json items are exchange shapes assembled from the run's ledger rows and validated against schemas/*.schema.json",
                "inspect/*.json and demo-artifact.json and health.json are verbatim CLI outputs (stable ids redacted by CLI default)",
                "resolution evidence_digest values are RFC 8785 canonical digests of the stored resolution evidence (no Q2 producer exists yet)",
                "scenario labels: " + json.dumps(ids),
            ],
        }

        manifest_lines = []
        for name in sorted(files):
            content = json.dumps(files[name], indent=2, sort_keys=False) + "\n"
            path = OUT / name
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_text(content)
            digest = hashlib.sha256(content.encode()).hexdigest()
            manifest_lines.append(f"{digest}  canonical/{name}")
        (WEB / "fixtures" / "manifest.sha256").write_text("\n".join(manifest_lines) + "\n")
        print(f"wrote {len(files)} fixture files + manifest")
        print(json.dumps(ids, indent=2))
    finally:
        refdest.kill()
        refdest.wait(timeout=10)


if __name__ == "__main__":
    main()
