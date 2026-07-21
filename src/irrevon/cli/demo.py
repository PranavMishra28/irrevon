"""``irrevon demo`` — the flagship script (RFC-001 §3/§9.5; RFC-002 §12).

Fixture-driven, two legs, one identical fault schedule:

- **Irrevon leg**: register → persist → dispatch → the effect succeeds at the
  destination but the response is lost on cue → the engine process is REALLY
  SIGKILLed → restart → recovery reconciles by query → SETTLED_COMMITTED +
  CONFIRMED_UNIQUE → a re-synthesized retry (different model arguments, SAME
  stable ids) collapses to the same effect_id and is rejected by the gate with
  evidence. One destination effect.
- **B5 contrast leg**: the strongest conventional baseline (durable runtime,
  stable op-IDs, native idempotency keys SENT) under the identical schedule
  retries on restart; the C2 destination ignores the key. Two destination
  effects, proven by read-back.

Exit 0 only when the contrast holds (Irrevon leg clean AND B5 leg duplicates);
exit 3 otherwise — the B5 leg is NEVER weakened to force exit 0 (master doc
§8.3/§8.6; the assertion direction is pinned in tests/e2e/ as well).
"""

from __future__ import annotations

import json
import os
import signal
import subprocess
import sys
import tempfile
import time
import urllib.request
from datetime import UTC, datetime
from pathlib import Path
from typing import Any, TextIO

import psycopg
from psycopg import sql
from psycopg.rows import dict_row

from irrevon.adapters.base import declarations_dir, load_declaration
from irrevon.adapters.refdest import RefdestAdapter
from irrevon.api.baselines import B5DurableRuntime
from irrevon.cli.config import Config
from irrevon.ledger.db import apply_migrations

# ── The frozen demo fixture (fixture-driven; not generated at run time) ───────

DEMO_STABLE_IDS = {"order_id": "9410", "customer_ref": "C-0007"}
DEMO_SCOPE = "acme-store/prod"
DEMO_EFFECT_TYPE = "order.create"

DEMO_PARAMETERS_ORIGINAL = {
    "line_items": [{"sku": "SKU-118", "quantity": 2}],
    "shipping_method": "standard",
    "note": "please deliver to the loading dock",
}
# The frozen re-synthesized variant: a model retrying "the same order" with
# different wording and argument shapes — same business intent, same stable ids.
DEMO_PARAMETERS_RESYNTHESIZED = {
    "items": [{"sku": "SKU-118", "qty": 2, "gift_wrap": False}],
    "shipping": {"method": "standard", "priority": "normal"},
    "customer_note": "Deliver at loading dock please!",
}


def _contract(parameters: dict[str, Any], authority_ref: str) -> dict[str, Any]:
    return {
        "schema_version": "1",
        "stable_ids": dict(DEMO_STABLE_IDS),
        "effect_type": DEMO_EFFECT_TYPE,
        "effect_class": "IRREVERSIBLE",
        "scope": DEMO_SCOPE,
        "adapter_id": "refdest-c2",
        "parameters": parameters,
        "authority_ref": authority_ref,
        "stamped_at": datetime.now(UTC).isoformat().replace("+00:00", "Z"),
    }


class _Emitter:
    def __init__(self, jsonl: bool, out: TextIO) -> None:
        self.jsonl = jsonl
        self.out = out

    def event(self, name: str, narrative: str, **fields: Any) -> None:
        if self.jsonl:
            print(json.dumps({"event": name, **fields}, default=str), file=self.out)
        else:
            print(f"  • {narrative}", file=self.out)

    def section(self, title: str) -> None:
        if not self.jsonl:
            print(f"\n── {title} " + "─" * max(0, 60 - len(title)), file=self.out)


class _Worker:
    """One real engine process (SIGKILL-able)."""

    def __init__(self, dsn: str, refdest_url: str) -> None:
        self.proc = subprocess.Popen(
            [sys.executable, "-m", "irrevon.api.worker"],
            stdin=subprocess.PIPE,
            stdout=subprocess.PIPE,
            stderr=subprocess.DEVNULL,
            text=True,
            env={
                **os.environ,
                "IRREVON_DSN": dsn,
                "IRREVON_REFDEST_URL": refdest_url,
                "IRREVON_REREAD_GAP_S": "0",
            },
        )
        self.recovery = self._wait("RECOVERY DONE")
        self._wait("READY")

    def _wait(self, prefix: str, timeout_s: float = 60.0) -> str:
        assert self.proc.stdout is not None
        deadline = time.monotonic() + timeout_s
        while time.monotonic() < deadline:
            line = self.proc.stdout.readline()
            if not line:
                raise RuntimeError(f"engine worker died waiting for {prefix!r}")
            if line.startswith(prefix):
                return str(line.strip())
        raise TimeoutError(f"no {prefix!r} sentinel")

    def send(self, command: str) -> dict[str, Any]:
        assert self.proc.stdin is not None
        self.proc.stdin.write(command + "\n")
        self.proc.stdin.flush()
        line = self._wait("RESULT ")
        loaded = json.loads(line.removeprefix("RESULT "))
        return dict(loaded)

    def sigkill(self) -> int:
        os.kill(self.proc.pid, signal.SIGKILL)
        return self.proc.wait(timeout=30)

    def exit(self) -> None:
        if self.proc.poll() is None:
            assert self.proc.stdin is not None
            self.proc.stdin.write("EXIT\n")
            self.proc.stdin.flush()
            self.proc.wait(timeout=10)


def _control(base_url: str, path: str, body: dict[str, Any] | None = None) -> Any:
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


def _demo_dsn(config: Config, seed: int) -> tuple[str, str]:
    base = config.resolved_dsn()
    demo_db = f"irrevon_demo_s{seed}"
    return psycopg.conninfo.make_conninfo(base, dbname=demo_db), demo_db


def _reset_demo_database(config: Config, seed: int) -> str:
    demo_dsn, demo_db = _demo_dsn(config, seed)
    with psycopg.connect(config.resolved_dsn(), autocommit=True) as admin:
        admin.execute(
            """
            SELECT pg_terminate_backend(pid) FROM pg_stat_activity
            WHERE datname = %s AND pid <> pg_backend_pid()
            """,
            (demo_db,),
        )
        admin.execute(
            sql.SQL("DROP DATABASE IF EXISTS {}").format(sql.Identifier(demo_db))
        )
        admin.execute(sql.SQL("CREATE DATABASE {}").format(sql.Identifier(demo_db)))
    apply_migrations(demo_dsn)
    return demo_dsn


def _sql(dsn: str, query: str, params: tuple[Any, ...] = ()) -> list[dict[str, Any]]:
    with psycopg.connect(dsn, row_factory=dict_row) as conn:
        return [dict(r) for r in conn.execute(query, params).fetchall()]


def run_demo(
    config: Config, *, seed: int, leg: str, keep: bool, jsonl: bool
) -> int:
    emit = _Emitter(jsonl, sys.stdout)
    refdest_proc = subprocess.Popen(
        [sys.executable, "-m", "irrevon.adapters.refdest_server", "--port", "0",
         "--seed", str(seed)],
        stdout=subprocess.PIPE,
        stderr=subprocess.DEVNULL,
        text=True,
    )
    assert refdest_proc.stdout is not None
    ready = refdest_proc.stdout.readline().strip()
    base_url = f"http://127.0.0.1:{int(ready.rsplit(' ', 1)[1])}"

    irrevon_leg: dict[str, Any] = {}
    b5_leg: dict[str, Any] = {}
    demo_dsn = ""
    try:
        if leg in ("irrevon", "both"):
            demo_dsn = _reset_demo_database(config, seed)
            irrevon_leg = _run_irrevon_leg(emit, demo_dsn, base_url)
        if leg in ("b5", "both"):
            _control(base_url, "/control/reset", {"seed": seed})
            b5_leg = _run_b5_leg(emit, base_url)
    finally:
        refdest_proc.kill()
        refdest_proc.wait(timeout=10)
        if not keep and demo_dsn:
            with psycopg.connect(config.resolved_dsn(), autocommit=True) as admin:
                admin.execute(
                    sql.SQL("DROP DATABASE IF EXISTS {}").format(
                        sql.Identifier(f"irrevon_demo_s{seed}")
                    )
                )

    # The contrast: Irrevon leg clean AND B5 leg duplicates. NEVER weakened to
    # force exit 0 (§8.3/§8.6): if B5 stops duplicating, the premise is wrong
    # and must surface as a failure — exit 3, not a patched assertion.
    contrast_holds = True
    if leg in ("irrevon", "both"):
        contrast_holds &= (
            irrevon_leg.get("destination_effects") == 1
            and irrevon_leg.get("duplicate_rejected") is True
            and irrevon_leg.get("reconciled") == "SETTLED_COMMITTED"
        )
    if leg in ("b5", "both"):
        contrast_holds &= (
            b5_leg.get("destination_effects") == 2
            and b5_leg.get("duplicate_created") is True
        )

    summary = {
        "schema_version": "1",
        "seed": seed,
        "irrevon_leg": irrevon_leg,
        "b5_leg": b5_leg,
        "contrast_holds": contrast_holds,
    }
    if jsonl:
        print(json.dumps(summary, default=str))
    else:
        emit.section("The contrast")
        n_irrevon = irrevon_leg.get("destination_effects", "-")
        n_b5 = b5_leg.get("destination_effects", "-")
        print(
            "\n  leg                           dest effects   duplicate?\n"
            "  ───────────────────────────── ────────────── ──────────────────\n"
            f"  Irrevon (reconcile-by-query)   {n_irrevon!s:>12}   rejected + cited\n"
            f"  B5 (durable retry + keys)     {n_b5!s:>12}   CREATED\n"
            f"\n  contrast holds: {contrast_holds}"
        )
        if irrevon_leg.get("effect_id") and keep:
            print(
                f"\n  inspect it: irrevon inspect {irrevon_leg['effect_id']} "
                f"--dsn '{demo_dsn}'"
            )
    return 0 if contrast_holds else 3


def _run_irrevon_leg(
    emit: _Emitter, demo_dsn: str, base_url: str
) -> dict[str, Any]:
    emit.section("Leg 1 — Irrevon")
    worker = _Worker(demo_dsn, base_url)
    reg = worker.send(
        "REGISTER " + json.dumps(_contract(DEMO_PARAMETERS_ORIGINAL, "auth_approved_task_18"))
    )
    effect_id = reg["effect_id"]
    emit.event(
        "registered",
        f"intent registered: order_id 9410 → effect {effect_id[:12]}… (PERSISTED)",
        effect_id=effect_id,
        lifecycle=reg["lifecycle"],
    )

    _control(base_url, "/control/schedule", {
        "entries": [{"match": {"op": "create"}, "fault": "DROP_RESPONSE_AFTER_COMMIT"}]
    })
    result = worker.send("DISPATCH " + effect_id)
    emit.event(
        "dispatch_response_lost",
        "dispatched; the destination committed the order but the response was "
        f"lost on cue → {result['lifecycle']} (evidence recorded)",
        effect_id=effect_id,
        fault="response_lost",
        lifecycle=result["lifecycle"],
    )

    exit_code = worker.sigkill()
    emit.event(
        "crash",
        f"engine process SIGKILLed (exit {exit_code}) — a real crash, mid-doubt",
        exit_status=exit_code,
    )

    worker2 = _Worker(demo_dsn, base_url)
    emit.event(
        "recovered",
        f"restart: {worker2.recovery.removeprefix('RECOVERY DONE ').strip()} — "
        "recovery queried the destination BEFORE any new dispatch",
        recovery=json.loads(worker2.recovery.removeprefix("RECOVERY DONE ")),
    )
    frontier = _sql(
        demo_dsn, "SELECT frontier FROM effect_frontiers WHERE effect_id = %s",
        (effect_id,),
    )[0]["frontier"]
    findings = _sql(
        demo_dsn, "SELECT classification FROM findings WHERE effect_id = %s",
        (effect_id,),
    )
    emit.event(
        "settled_confirmed_unique",
        f"the order exists exactly once → {frontier} + "
        f"{findings[0]['classification'] if findings else '?'}",
        lifecycle=frontier,
        classification=findings[0]["classification"] if findings else None,
    )

    retry = worker2.send(
        "REGISTER "
        + json.dumps(_contract(DEMO_PARAMETERS_RESYNTHESIZED, "auth_approved_task_22"))
    )
    emit.event(
        "resynthesis_collapsed",
        "the agent retries with re-synthesized arguments (different wording, "
        f"same order_id 9410) → SAME effect {retry['effect_id'][:12]}… "
        f"(replayed={retry['replayed']}, variant recorded)",
        effect_id=retry["effect_id"],
        replayed=retry["replayed"],
        parameter_variant=retry.get("parameter_variant_digest"),
    )
    deny = worker2.send("DISPATCH " + effect_id)
    emit.event(
        "duplicate_rejected",
        f"gate denies the retry: check={deny['deny_check']} citing the settled "
        "execution and the recorded parameter variant — the re-synthesis defeat",
        outcome=deny["outcome"],
        deny_check=deny["deny_check"],
        decision_id=deny["decision_id"],
    )
    worker2.exit()

    effects = list(_control(base_url, "/control/state")["effects"])
    return {
        "destination_effects": len(effects),
        "duplicate_rejected": deny["outcome"] == "denied"
        and deny["deny_check"] == "dedup",
        "reconciled": frontier,
        "effect_id": effect_id,
    }


def _run_b5_leg(emit: _Emitter, base_url: str) -> dict[str, Any]:
    emit.section(
        "Leg 2 — B5 baseline (durable runtime + stable op-IDs + idempotency keys)"
    )
    declaration = load_declaration(declarations_dir() / "refdest-c2.capability.json")
    adapter = RefdestAdapter("refdest-c2", declaration, base_url=base_url)
    _control(base_url, "/control/schedule", {
        "entries": [{"match": {"op": "create"}, "fault": "DROP_RESPONSE_AFTER_COMMIT"}]
    })

    with tempfile.TemporaryDirectory() as tmp:
        journal = Path(tmp) / "b5-journal.json"
        op_id = "wf-order-9410-activity-0"  # stable workflow op id

        b5 = B5DurableRuntime(journal, adapter)
        first = b5.execute(op_id, DEMO_EFFECT_TYPE, DEMO_PARAMETERS_ORIGINAL)
        emit.event(
            "b5_response_lost",
            "B5 dispatches with a stable op-ID and an idempotency key; the "
            f"destination commits; the response is lost → {first['transport_outcome']}",
            transport_outcome=first["transport_outcome"],
        )
        del b5  # the durable runtime's process dies (journal survives)
        emit.event("b5_restart", "B5 restarts from its durable journal")

        recovered = B5DurableRuntime(journal, adapter)
        retried = recovered.recover()
        emit.event(
            "b5_retried",
            "B5 retries the op with the SAME op-ID and key — the C2 "
            "destination accepts the key and ignores it",
            retried=[r["op_id"] for r in retried],
        )

    effects = _control(base_url, "/control/state")["effects"]
    n = len(effects)
    emit.event(
        "b5_duplicate",
        f"destination read-back: {n} effects for one intent — the duplicate "
        "HAPPENED (proven by read-back, not inferred)",
        destination_effects=n,
    )
    return {"destination_effects": n, "duplicate_created": n > 1}
