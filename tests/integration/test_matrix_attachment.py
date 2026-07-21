"""Exhaustive dimension A×B attachment matrix (RFC-002 §3.2; testing.md §4.3).

Conformance: master doc §12.1 row 3 — "Illegal lifecycle × classification
combinations rejected" (M3), A×B leg — all 7 lifecycle states × 5
classifications = 35 cells, plus the destination-keyed ORPHANED path (master
doc §12.1 row 7 precondition: orphans representable WITHOUT a ledger record).
Oracle: detent.statetable.LEGAL_ATTACHMENTS (validated against the SQL seed in
test_state_seed.py); a meta-test guarantees every cell is asserted.
"""

from __future__ import annotations

import psycopg
import pytest
from psycopg.types.json import Jsonb

from detent.statetable import (
    CLASSIFICATIONS,
    LEGAL_ATTACHMENTS,
    LIFECYCLE_STATES,
)
from tests.integration.conftest import DBHandles
from tests.integration.driver import admin_conn, make_effect, make_execution_at

pytestmark = pytest.mark.integration

_CELLS = [(state, cls) for state in LIFECYCLE_STATES for cls in CLASSIFICATIONS]


def test_meta_all_35_cells_enumerated() -> None:
    assert len(_CELLS) == 35
    # Every legal cell is among the enumerated ones (nothing outside the grid).
    assert set(LEGAL_ATTACHMENTS) <= set(_CELLS)


def _attach(
    conn: psycopg.Connection[dict[str, object]],
    effect_id: str | None,
    classification: str,
    destination_ref: str | None = None,
) -> int:
    row = conn.execute(
        "SELECT ledger_attach_finding(%s, 'refdest-c2', %s, %s, %s, %s, 'sha256:0', "
        "'reconciler') AS fid",
        (
            effect_id,
            destination_ref,
            classification,
            1 if classification == "DUPLICATE" else None,
            Jsonb({"probe_ids": [1]}),
        ),
    ).fetchone()
    assert row is not None
    return int(row["fid"])  # type: ignore[arg-type]


@pytest.mark.parametrize(
    ("frontier", "classification"), _CELLS, ids=[f"{s}x{c}" for s, c in _CELLS]
)
def test_attachment_cell(
    frontier: str, classification: str, fresh_db: DBHandles
) -> None:
    legal = (frontier, classification) in LEGAL_ATTACHMENTS
    with admin_conn(fresh_db.admin_dsn) as conn:
        effect_id = make_effect(conn)
        make_execution_at(conn, effect_id, frontier)
        if legal:
            finding_id = _attach(conn, effect_id, classification)
            row = conn.execute(
                "SELECT classification FROM findings WHERE finding_id = %s",
                (finding_id,),
            ).fetchone()
            assert row is not None and row["classification"] == classification
        else:
            before = conn.execute("SELECT count(*) AS n FROM findings").fetchone()
            with pytest.raises(psycopg.Error) as excinfo:
                _attach(conn, effect_id, classification)
            assert excinfo.value.sqlstate == "DT003", (
                f"{frontier}×{classification}: expected DT003, got "
                f"{excinfo.value.sqlstate}"
            )
            after = conn.execute("SELECT count(*) AS n FROM findings").fetchone()
            assert before is not None and after is not None
            assert after["n"] == before["n"], "illegal attach must write nothing"


def test_orphaned_is_destination_keyed_only(fresh_db: DBHandles) -> None:
    """ORPHANED attaches to (adapter_id, destination_ref), never to a record —
    and no EffectRecord row is created for it (RFC-001 §2 dimension-B rule)."""
    with admin_conn(fresh_db.admin_dsn) as conn:
        records_before = conn.execute(
            "SELECT count(*) AS n FROM effect_records"
        ).fetchone()
        finding_id = _attach(conn, None, "ORPHANED", destination_ref="dest_oob_1")
        row = conn.execute(
            "SELECT effect_id, destination_ref FROM findings WHERE finding_id = %s",
            (finding_id,),
        ).fetchone()
        assert row is not None
        assert row["effect_id"] is None
        assert row["destination_ref"] == "dest_oob_1"
        records_after = conn.execute(
            "SELECT count(*) AS n FROM effect_records"
        ).fetchone()
        assert records_before is not None and records_after is not None
        assert records_after["n"] == records_before["n"]

        # Idempotence arbiter: one ORPHANED finding per (adapter, destination_ref).
        with pytest.raises(psycopg.errors.UniqueViolation):
            _attach(conn, None, "ORPHANED", destination_ref="dest_oob_1")


def test_record_less_non_orphaned_rejected(fresh_db: DBHandles) -> None:
    with admin_conn(fresh_db.admin_dsn) as conn:
        with pytest.raises(psycopg.Error) as excinfo:
            _attach(conn, None, "LOST", destination_ref="dest_x")
        assert excinfo.value.sqlstate == "DT003"


def test_confirmed_unique_auto_resolves_and_closes(fresh_db: DBHandles) -> None:
    """§3.3: CONFIRMED_UNIQUE is auto-ACCEPTED_AS_IS (system actor) and CLOSED
    in the same transaction as the attach."""
    with admin_conn(fresh_db.admin_dsn) as conn:
        effect_id = make_effect(conn)
        make_execution_at(conn, effect_id, "SETTLED_COMMITTED")
        finding_id = _attach(conn, effect_id, "CONFIRMED_UNIQUE")
        chain = conn.execute(
            """
            SELECT from_status, to_status, actor FROM finding_resolutions
            WHERE finding_id = %s ORDER BY resolution_seq
            """,
            (finding_id,),
        ).fetchall()
        assert [(r["from_status"], r["to_status"], r["actor"]) for r in chain] == [
            ("OPEN", "ACCEPTED_AS_IS", "system"),
            ("ACCEPTED_AS_IS", "CLOSED", "system"),
        ]


def test_duplicate_requires_excess_count(fresh_db: DBHandles) -> None:
    """DUPLICATE keeps the canonical n>1 meaning (AM-18): excess_effect_count
    = n − 1 ≥ 1 is mandatory."""
    with admin_conn(fresh_db.admin_dsn) as conn:
        effect_id = make_effect(conn)
        make_execution_at(conn, effect_id, "SETTLED_COMMITTED")
        with pytest.raises(psycopg.errors.CheckViolation):
            conn.execute(
                "SELECT ledger_attach_finding(%s, 'refdest-c2', NULL, 'DUPLICATE', "
                "NULL, %s, 'sha256:0', 'reconciler')",
                (effect_id, Jsonb({"probe_ids": [1]})),
            )
