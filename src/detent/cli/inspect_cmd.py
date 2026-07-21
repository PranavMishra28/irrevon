"""``detent inspect <id>`` — the ledger-only evidence view (RFC-002 §11).

Transition history, contract summary (stable-id KEYS; values redacted by
default, ``--reveal`` local), receipts across all attempts and executions,
findings with full resolution history, gate history, a merged timeline, and an
integrity section that recomputes ``intent_id`` from the stored canonical
contract bytes and compares — a mismatch is a ledger-integrity incident signal.
Exit codes: 0 found · 3 not found · 1 crash · 2 usage.
"""

from __future__ import annotations

import hashlib
import json
from typing import Any

import psycopg
from psycopg.rows import dict_row

from detent.identity import INTENT_ID_RE

__all__ = ["run_inspect"]


def _rows(
    conn: psycopg.Connection[dict[str, Any]], query: str, params: tuple[Any, ...]
) -> list[dict[str, Any]]:
    return [dict(r) for r in conn.execute(query, params).fetchall()]


def run_inspect(
    dsn: str, identifier: str, *, reveal: bool, as_json: bool
) -> int:
    with psycopg.connect(dsn, row_factory=dict_row) as conn:
        if INTENT_ID_RE.match(identifier):
            return _inspect_effect(conn, identifier, reveal=reveal, as_json=as_json)
        return _inspect_destination_ref(conn, identifier, as_json=as_json)


def _inspect_effect(
    conn: psycopg.Connection[dict[str, Any]],
    effect_id: str,
    *,
    reveal: bool,
    as_json: bool,
) -> int:
    record_rows = _rows(
        conn, "SELECT * FROM effect_records WHERE effect_id = %s", (effect_id,)
    )
    if not record_rows:
        print(f"not found: {effect_id}")
        return 3
    record = record_rows[0]

    transitions = _rows(
        conn,
        """
        SELECT t.transition_seq, e.step, e.operation_id, t.from_state, t.to_state,
               t.cause, t.actor, t.evidence, t.created_at
        FROM effect_transitions t JOIN effect_executions e USING (execution_id)
        WHERE e.effect_id = %s ORDER BY t.transition_seq
        """,
        (effect_id,),
    )
    receipts = _rows(
        conn,
        """
        SELECT r.receipt_id, e.operation_id, a.attempt_no, a.kind,
               a.idempotency_key, r.transport_outcome, r.failure_kind,
               r.destination_ref, r.recorded_by, r.recorded_at
        FROM dispatch_receipts r
        JOIN dispatch_attempts a USING (attempt_id)
        JOIN effect_executions e USING (execution_id)
        WHERE e.effect_id = %s ORDER BY r.receipt_id
        """,
        (effect_id,),
    )
    findings = _rows(
        conn,
        "SELECT * FROM findings WHERE effect_id = %s ORDER BY finding_id",
        (effect_id,),
    )
    resolutions = _rows(
        conn,
        """
        SELECT r.* FROM finding_resolutions r JOIN findings f USING (finding_id)
        WHERE f.effect_id = %s ORDER BY r.resolution_seq
        """,
        (effect_id,),
    )
    decisions = _rows(
        conn,
        """
        SELECT decision_id, variant, outcome, deny_check, checks, evidence, created_at
        FROM gate_decisions WHERE effect_id = %s ORDER BY decision_id
        """,
        (effect_id,),
    )
    probes = _rows(
        conn,
        """
        SELECT p.probe_id, p.probe_kind, p.result, p.n_found, p.queried_at
        FROM status_probes p JOIN effect_executions e USING (execution_id)
        WHERE e.effect_id = %s ORDER BY p.probe_id
        """,
        (effect_id,),
    )

    # Integrity: recompute intent_id from the stored canonical contract bytes.
    canonical: bytes = bytes(record["contract_canonical"])
    recomputed = hashlib.sha256(canonical).hexdigest()
    integrity_ok = recomputed == effect_id

    stable_ids = dict(record["stable_ids"])
    shown_ids: dict[str, str] = (
        stable_ids
        if reveal
        else dict.fromkeys(stable_ids, "<redacted; --reveal to show>")
    )
    classification = findings[-1]["classification"] if findings else "UNRECONCILED"
    frontier_rows = _rows(
        conn,
        "SELECT frontier FROM effect_frontiers WHERE effect_id = %s",
        (effect_id,),
    )
    lifecycle = frontier_rows[0]["frontier"] if frontier_rows else "INTENDED"

    if as_json:
        print(
            json.dumps(
                {
                    "schema_version": "1",
                    "kind": "effect",
                    "record": {
                        "effect_id": effect_id,
                        "effect_type": record["effect_type"],
                        "effect_class": record["effect_class"],
                        "scope": record["scope"],
                        "stable_ids": shown_ids,
                        "adapter_id": record["adapter_id"],
                        "lifecycle": lifecycle,
                    },
                    "timeline": transitions,
                    "receipts": receipts,
                    "findings": findings,
                    "resolutions": resolutions,
                    "gate_decisions": decisions,
                    "probes": probes,
                    "classification": classification,
                    "integrity": {
                        "recomputed_intent_id": recomputed,
                        "matches": integrity_ok,
                    },
                },
                default=str,
            )
        )
        return 0 if integrity_ok else 4

    print(f"effect {effect_id}")
    print(f"  type={record['effect_type']} class={record['effect_class']} "
          f"scope={record['scope']} adapter={record['adapter_id']}")
    print(f"  stable ids: {shown_ids}")
    print(f"  classification: {classification}")
    print("\n  lifecycle timeline:")
    for t in transitions:
        frm = t["from_state"] or "∅"
        print(
            f"    [{t['created_at']}] step {t['step']}: {frm} → {t['to_state']} "
            f"({t['cause']}, {t['actor']})"
        )
    if receipts:
        print("\n  receipts (all attempts, all executions):")
        for r in receipts:
            print(
                f"    rcpt_{r['receipt_id']:020d} op={r['operation_id'][:12]}… "
                f"attempt {r['attempt_no']} ({r['kind']}): "
                f"{r['transport_outcome']}"
                + (f"/{r['failure_kind']}" if r["failure_kind"] else "")
                + (f" ref={r['destination_ref']}" if r["destination_ref"] else "")
                + f" by {r['recorded_by']}"
            )
    if decisions:
        print("\n  gate history:")
        for d in decisions:
            line = f"    decision {d['decision_id']} [{d['variant']}]: {d['outcome']}"
            if d["deny_check"]:
                line += f" (check={d['deny_check']})"
            print(line)
    if probes:
        print("\n  probes:")
        for p in probes:
            print(
                f"    probe {p['probe_id']} ({p['probe_kind']}): {p['result']}"
                + (f" n={p['n_found']}" if p["n_found"] is not None else "")
            )
    if findings:
        print("\n  findings:")
        for f in findings:
            chain = [
                f"{r['from_status']}→{r['to_status']}"
                for r in resolutions
                if r["finding_id"] == f["finding_id"]
            ]
            print(
                f"    fnd_{f['finding_id']:020d}: {f['classification']}"
                + (
                    f" excess={f['excess_effect_count']}"
                    if f["excess_effect_count"] is not None
                    else ""
                )
                + f" evidence={f['evidence_digest'][:23]}… "
                + (f"resolution: {' '.join(chain)}" if chain else "resolution: OPEN")
            )
    print("\n  integrity:")
    print(f"    stored canonical bytes → sha256 = {recomputed[:16]}…")
    print(
        "    matches effect_id: "
        + ("YES (ledger integrity holds)" if integrity_ok else
           "NO — LEDGER-INTEGRITY INCIDENT (master doc §12.4)")
    )
    return 0 if integrity_ok else 4


def _inspect_destination_ref(
    conn: psycopg.Connection[dict[str, Any]], ref: str, *, as_json: bool
) -> int:
    findings = _rows(
        conn,
        "SELECT * FROM findings WHERE destination_ref = %s ORDER BY finding_id",
        (ref,),
    )
    if not findings:
        print(f"not found: {ref}")
        return 3
    if as_json:
        print(
            json.dumps(
                {"schema_version": "1", "kind": "destination_ref",
                 "findings": findings},
                default=str,
            )
        )
        return 0
    print(f"destination_ref {ref} (orphans have no effect record — §7.1):")
    for f in findings:
        print(
            f"  fnd_{f['finding_id']:020d}: {f['classification']} "
            f"adapter={f['adapter_id']} evidence={f['evidence_digest'][:23]}…"
        )
    return 0
