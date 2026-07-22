"""``irrevon inspect <id>`` — the ledger-only evidence view (RFC-002 §11).

Transition history, contract summary (stable-id KEYS; values redacted by
default, ``--reveal`` local), receipts across all attempts and executions,
findings with full resolution history, gate history, a merged timeline, and an
integrity section that recomputes ``intent_id`` from the stored canonical
contract bytes and compares — a mismatch is a ledger-integrity incident signal.

The JSON document is produced by :func:`irrevon.api.readviews.inspect_payload`
— the SAME producer ``irrevon serve`` uses for
``GET /api/v1/effects/{id}/inspect`` (single-producer rule; byte-parity is
test-locked in ``tests/serve/``).
Exit codes: 0 found · 3 not found · 1 crash · 2 usage · 4 integrity mismatch.
"""

from __future__ import annotations

import json
from typing import Any

import psycopg
from psycopg.rows import dict_row

from irrevon.api.readviews import inspect_payload
from irrevon.identity import INTENT_ID_RE

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
    payload = inspect_payload(conn, effect_id, reveal=reveal)
    if payload is None:
        print(f"not found: {effect_id}")
        return 3
    integrity_ok = bool(payload["integrity"]["matches"])

    if as_json:
        print(json.dumps(payload, default=str))
        return 0 if integrity_ok else 4

    record = payload["record"]
    transitions = payload["timeline"]
    receipts = payload["receipts"]
    findings = payload["findings"]
    resolutions = payload["resolutions"]
    decisions = payload["gate_decisions"]
    probes = payload["probes"]
    recomputed = payload["integrity"]["recomputed_intent_id"]

    print(f"effect {effect_id}")
    print(f"  type={record['effect_type']} class={record['effect_class']} "
          f"scope={record['scope']} adapter={record['adapter_id']}")
    print(f"  stable ids: {record['stable_ids']}")
    print(f"  classification: {payload['classification']}")
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
