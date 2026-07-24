"""Shared read-surface producers (RFC-002 §9) — ONE producer per payload.

``irrevon inspect --json`` and ``GET /api/v1/effects/{id}/inspect`` call the
same :func:`inspect_payload`; the Q1/Q2 list envelopes reproduce the fixture
capture pipeline's record/finding exchange shapes (``web/scripts/
capture-fixtures.py`` is the reference — the committed workbench fixtures ARE
this module's output shape, validated against ``schemas/*.schema.json``).

Everything here is read-only SELECT SQL; the locked write path stays in
``irrevon.ledger``. Query-parameter validation raises :class:`QueryInvalid`
(serve maps it to 400 ``query_invalid``).
"""

from __future__ import annotations

import base64
import binascii
import hashlib
import json
from datetime import UTC, datetime
from typing import Any

import psycopg
import rfc8785

from irrevon import statetable

__all__ = [
    "QueryInvalid",
    "decode_cursor",
    "effect_item",
    "encode_cursor",
    "inspect_payload",
    "iso",
    "list_effects",
    "list_findings",
]

_LIFECYCLES = frozenset(statetable.LIFECYCLE_STATES)
_CLASSIFICATIONS = frozenset(statetable.CLASSIFICATIONS) | {"UNRECONCILED"}
_RESOLUTION_STATUSES = frozenset(statetable.RESOLUTION_STATUSES)

_MAX_LIMIT = 500
_DEFAULT_LIMIT = 50


class QueryInvalid(ValueError):
    """A malformed query parameter (bad timestamp, bad cursor, non-enum value)."""


def iso(value: Any) -> str:
    """RFC 3339 with a ``Z`` suffix — the exchange-shape timestamp format."""
    if isinstance(value, datetime):
        return value.astimezone(UTC).isoformat().replace("+00:00", "Z")
    return str(value)


def _rows(
    conn: psycopg.Connection[dict[str, Any]], query: str, params: tuple[Any, ...]
) -> list[dict[str, Any]]:
    return [dict(r) for r in conn.execute(query, params).fetchall()]


def _digest_stable_ids(stable_ids: dict[str, Any]) -> dict[str, str]:
    """Preserve identity field names while removing upstream values.

    The digest is deterministic so an operator can compare recorded views, but
    it is not anonymization: low-entropy identifiers may be guessable. Raw
    values are available only through local ``inspect --reveal`` (ADR-0036).
    """
    return {
        key: f"sha256:{hashlib.sha256(str(value).encode('utf-8')).hexdigest()}"
        for key, value in stable_ids.items()
    }


# ── inspect (the single producer behind CLI and serve) ────────────────────────


def inspect_payload(
    conn: psycopg.Connection[dict[str, Any]], effect_id: str, *, reveal: bool
) -> dict[str, Any] | None:
    """The verbatim ``irrevon inspect --json`` document, or ``None`` when the
    effect does not exist. Timestamps stay raw ``datetime`` objects; both
    consumers serialize with ``json.dumps(..., default=str)`` so the bytes
    match by construction (the byte-parity test locks this)."""
    record_rows = _rows(
        conn, "SELECT * FROM effect_records WHERE effect_id = %s", (effect_id,)
    )
    if not record_rows:
        return None
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

    stable_ids = dict(record["stable_ids"])
    shown_ids = stable_ids if reveal else _digest_stable_ids(stable_ids)
    classification = findings[-1]["classification"] if findings else "UNRECONCILED"
    frontier_rows = _rows(
        conn,
        "SELECT frontier FROM effect_frontiers WHERE effect_id = %s",
        (effect_id,),
    )
    lifecycle = frontier_rows[0]["frontier"] if frontier_rows else "INTENDED"

    return {
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
            "matches": recomputed == effect_id,
        },
    }


# ── exchange shapes (Q1/Q2 items; capture-pipeline parity) ────────────────────


def _record_exchange(
    conn: psycopg.Connection[dict[str, Any]], rec: dict[str, Any]
) -> dict[str, Any]:
    """EffectRecord exchange shape (schemas/effect-record.schema.json) for one
    ``effect_records`` row — the capture pipeline's record view."""
    effect_id = rec["effect_id"]
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
    lifecycle_at = conn.execute(
        """
        SELECT t.created_at FROM effect_transitions t
        JOIN effect_executions e USING (execution_id)
        WHERE e.effect_id = %s ORDER BY t.transition_seq DESC LIMIT 1
        """,
        (effect_id,),
    ).fetchone()
    # Authority linkage lives in the authorities adjunct tables (RFC-002 §2.2).
    authority = conn.execute(
        """
        SELECT a.authority_ref, a.stamped_at
        FROM effect_authorities ea JOIN authorities a USING (authority_id)
        WHERE ea.effect_id = %s ORDER BY ea.link_id LIMIT 1
        """,
        (effect_id,),
    ).fetchone()
    if frontier is None or lifecycle_at is None or authority is None:
        raise RuntimeError(f"effect {effect_id} is missing adjunct rows")
    out: dict[str, Any] = {
        "schema_version": "1",
        "effect_id": effect_id,
        "operation_id": frontier["operation_id"],
        "step": frontier["step"],
        "effect_type": rec["effect_type"],
        "effect_class": rec["effect_class"],
        "scope": rec["scope"],
        # Preserve field names for identity reasoning without returning
        # upstream values from the HTTP surface (ADR-0036).
        "stable_ids": _digest_stable_ids(dict(rec["stable_ids"])),
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


def _finding_exchange(
    conn: psycopg.Connection[dict[str, Any]], row: dict[str, Any]
) -> dict[str, Any]:
    """ReconciliationFinding exchange shape for one ``findings`` row —
    digest-only evidence per RFC-002 §9 until the redaction pipeline exists."""
    resolutions = _rows(
        conn,
        """
        SELECT * FROM finding_resolutions WHERE finding_id = %s
        ORDER BY resolution_seq
        """,
        (row["finding_id"],),
    )
    resolution: dict[str, Any]
    if resolutions:
        last = resolutions[-1]
        resolution = {"status": last["to_status"]}
        if last["to_status"] != "OPEN":
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
        "evidence": {
            "digest": row["evidence_digest"],
            "bundle": None,
            "redaction": "digest_only",
        },
        "created_by": row["created_by"],
        "created_at": iso(row["created_at"]),
        "resolution": resolution,
    }
    if row["classification"] == "DUPLICATE":
        out["excess_effect_count"] = row["excess_effect_count"]
    return out


def _latest_finding(
    conn: psycopg.Connection[dict[str, Any]], effect_id: str
) -> dict[str, Any] | None:
    row = conn.execute(
        """
        SELECT * FROM findings WHERE effect_id = %s
        ORDER BY finding_id DESC LIMIT 1
        """,
        (effect_id,),
    ).fetchone()
    return dict(row) if row is not None else None


def _item_for(
    conn: psycopg.Connection[dict[str, Any]], rec: dict[str, Any]
) -> dict[str, Any]:
    """Q1 item: {record, classification, finding} — the pinned lean shape."""
    finding_row = _latest_finding(conn, rec["effect_id"])
    return {
        "record": _record_exchange(conn, rec),
        "classification": (
            finding_row["classification"] if finding_row else "UNRECONCILED"
        ),
        "finding": _finding_exchange(conn, finding_row) if finding_row else None,
    }


# ── cursors (opaque keyset; dx-api §4) ────────────────────────────────────────


def encode_cursor(created_at: Any, id_value: str) -> str:
    doc = json.dumps({"c": iso(created_at), "id": id_value})
    return base64.urlsafe_b64encode(doc.encode("utf-8")).decode("ascii")


def decode_cursor(cursor: str) -> tuple[datetime, str]:
    try:
        loaded = json.loads(base64.urlsafe_b64decode(cursor.encode("ascii")))
        created_at = datetime.fromisoformat(str(loaded["c"]))
        id_value = str(loaded["id"])
    except (binascii.Error, ValueError, KeyError, TypeError, UnicodeDecodeError) as err:
        raise QueryInvalid(f"invalid cursor: {cursor!r}") from err
    return created_at, id_value


def _parse_timestamp(name: str, value: str) -> datetime:
    try:
        return datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError as err:
        raise QueryInvalid(f"invalid {name!r} timestamp: {value!r}") from err


def _clamp_limit(raw: str | None) -> int:
    if raw is None:
        return _DEFAULT_LIMIT
    try:
        value = int(raw)
    except ValueError as err:
        raise QueryInvalid(f"invalid limit: {raw!r}") from err
    if value < 1:
        raise QueryInvalid(f"invalid limit: {raw!r}")
    return min(value, _MAX_LIMIT)  # clamp, don't error (dx-api §4 Q1)


def _check_enum(name: str, values: list[str], allowed: frozenset[str]) -> None:
    for value in values:
        if value not in allowed:
            raise QueryInvalid(f"invalid {name!r} value: {value!r}")


def _as_of(conn: psycopg.Connection[dict[str, Any]]) -> str:
    row = conn.execute("SELECT now() AS now").fetchone()
    assert row is not None
    return iso(row["now"])


# ── Q1: effects ───────────────────────────────────────────────────────────────

_LATEST_CLASSIFICATION_SQL = (
    "COALESCE((SELECT fd.classification FROM findings fd "
    "WHERE fd.effect_id = r.effect_id "
    "ORDER BY fd.finding_id DESC LIMIT 1), 'UNRECONCILED')"
)


def list_effects(
    conn: psycopg.Connection[dict[str, Any]],
    *,
    scope: str | None = None,
    lifecycle: list[str] | None = None,
    classification: list[str] | None = None,
    effect_type: str | None = None,
    effect_class: str | None = None,
    time_from: str | None = None,
    time_to: str | None = None,
    limit: str | None = None,
    cursor: str | None = None,
) -> dict[str, Any]:
    """Q1 envelope — keyset pagination ordered ``created_at DESC,
    effect_id DESC`` (stable: the ledger is append-only)."""
    page_limit = _clamp_limit(limit)
    clauses: list[str] = []
    params: list[Any] = []
    if scope is not None:
        clauses.append("r.scope = %s")
        params.append(scope)
    if lifecycle:
        _check_enum("lifecycle", lifecycle, _LIFECYCLES)
        clauses.append("f.frontier = ANY(%s)")
        params.append(list(lifecycle))
    if classification:
        _check_enum("classification", classification, _CLASSIFICATIONS)
        clauses.append(f"{_LATEST_CLASSIFICATION_SQL} = ANY(%s)")
        params.append(list(classification))
    if effect_type is not None:
        clauses.append("r.effect_type = %s")
        params.append(effect_type)
    if effect_class is not None:
        clauses.append("r.effect_class = %s")
        params.append(effect_class)
    if time_from is not None:
        clauses.append("r.created_at >= %s")
        params.append(_parse_timestamp("from", time_from))
    if time_to is not None:
        clauses.append("r.created_at <= %s")
        params.append(_parse_timestamp("to", time_to))
    if cursor is not None:
        after_ts, after_id = decode_cursor(cursor)
        clauses.append("(r.created_at, r.effect_id) < (%s, %s)")
        params.extend((after_ts, after_id))

    where = ("WHERE " + " AND ".join(clauses)) if clauses else ""
    rows = _rows(
        conn,
        f"""
        SELECT r.* FROM effect_records r
        JOIN effect_frontiers f ON f.effect_id = r.effect_id
        {where}
        ORDER BY r.created_at DESC, r.effect_id DESC
        LIMIT %s
        """,
        (*params, page_limit + 1),
    )
    has_more = len(rows) > page_limit
    page = rows[:page_limit]
    next_cursor = (
        encode_cursor(page[-1]["created_at"], page[-1]["effect_id"])
        if has_more and page
        else None
    )
    return {
        "schema_version": "1",
        "data": [_item_for(conn, rec) for rec in page],
        "has_more": has_more,
        "next_cursor": next_cursor,
        "as_of": _as_of(conn),
    }


def effect_item(
    conn: psycopg.Connection[dict[str, Any]], effect_id: str
) -> dict[str, Any] | None:
    """Route 2: ``{schema_version, record, classification, finding}``."""
    rec = conn.execute(
        "SELECT * FROM effect_records WHERE effect_id = %s", (effect_id,)
    ).fetchone()
    if rec is None:
        return None
    return {"schema_version": "1", **_item_for(conn, dict(rec))}


# ── Q2: findings ──────────────────────────────────────────────────────────────

_LATEST_STATUS_SQL = (
    "COALESCE((SELECT fr.to_status FROM finding_resolutions fr "
    "WHERE fr.finding_id = fd.finding_id "
    "ORDER BY fr.resolution_seq DESC LIMIT 1), 'OPEN')"
)


def list_findings(
    conn: psycopg.Connection[dict[str, Any]],
    *,
    classification: list[str] | None = None,
    resolution_status: list[str] | None = None,
    subject_effect_id: str | None = None,
    adapter: str | None = None,
    destination_ref: str | None = None,
    time_from: str | None = None,
    time_to: str | None = None,
    limit: str | None = None,
    cursor: str | None = None,
) -> dict[str, Any]:
    """Q2 envelope — same keyset discipline as Q1, ordered ``created_at DESC,
    finding_id DESC``."""
    page_limit = _clamp_limit(limit)
    clauses: list[str] = []
    params: list[Any] = []
    if classification:
        _check_enum(
            "classification", classification, frozenset(statetable.CLASSIFICATIONS)
        )
        clauses.append("fd.classification = ANY(%s)")
        params.append(list(classification))
    if resolution_status:
        _check_enum("resolution_status", resolution_status, _RESOLUTION_STATUSES)
        clauses.append(f"{_LATEST_STATUS_SQL} = ANY(%s)")
        params.append(list(resolution_status))
    if subject_effect_id is not None:
        clauses.append("fd.effect_id = %s")
        params.append(subject_effect_id)
    if adapter is not None:
        clauses.append("fd.adapter_id = %s")
        params.append(adapter)
    if destination_ref is not None:
        clauses.append("fd.destination_ref = %s")
        params.append(destination_ref)
    if time_from is not None:
        clauses.append("fd.created_at >= %s")
        params.append(_parse_timestamp("from", time_from))
    if time_to is not None:
        clauses.append("fd.created_at <= %s")
        params.append(_parse_timestamp("to", time_to))
    if cursor is not None:
        after_ts, after_id = decode_cursor(cursor)
        try:
            after_num = int(after_id)
        except ValueError as err:
            raise QueryInvalid(f"invalid cursor: {cursor!r}") from err
        clauses.append("(fd.created_at, fd.finding_id) < (%s, %s)")
        params.extend((after_ts, after_num))

    where = ("WHERE " + " AND ".join(clauses)) if clauses else ""
    rows = _rows(
        conn,
        f"""
        SELECT fd.* FROM findings fd
        {where}
        ORDER BY fd.created_at DESC, fd.finding_id DESC
        LIMIT %s
        """,
        (*params, page_limit + 1),
    )
    has_more = len(rows) > page_limit
    page = rows[:page_limit]
    next_cursor = (
        encode_cursor(page[-1]["created_at"], str(page[-1]["finding_id"]))
        if has_more and page
        else None
    )
    return {
        "schema_version": "1",
        "data": [_finding_exchange(conn, row) for row in page],
        "has_more": has_more,
        "next_cursor": next_cursor,
        "as_of": _as_of(conn),
    }
