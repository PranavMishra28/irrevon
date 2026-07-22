"""Exhaustive dimension B×C resolution matrix (RFC-002 §3.3; testing.md §4.3).

Conformance: master doc §12.1 row 3 (M3), B×C leg — every classification ×
action cell asserted against ledger_resolve on real Postgres, plus the status
chain (OPEN → action → CLOSED; ESCALATED_HUMAN re-routing; first-write-wins).
Oracle: irrevon.statetable LEGAL_ACTIONS / LEGAL_STATUS_EDGES (validated against
the SQL seed by test_state_seed.py).
"""

from __future__ import annotations

import psycopg
import pytest
from psycopg.types.json import Jsonb

from irrevon.statetable import (
    CLASSIFICATIONS,
    LEGAL_ACTIONS,
    RESOLUTION_ACTIONS,
)
from tests.integration.conftest import DBHandles
from tests.integration.driver import admin_conn, make_effect, make_execution_at

pytestmark = pytest.mark.integration

# The legal frontier used to mint each classification's subject finding.
_HOME_FRONTIER = {
    "CONFIRMED_UNIQUE": "SETTLED_COMMITTED",
    "DUPLICATE": "SETTLED_COMMITTED",
    "LOST": "SETTLED_FAILED",
    "CONTRADICTED": "SETTLED_COMMITTED",
    "ORPHANED": None,  # destination-keyed
}

_CELLS = [(cls, action) for cls in CLASSIFICATIONS for action in RESOLUTION_ACTIONS]


def test_meta_all_20_cells_enumerated() -> None:
    assert len(_CELLS) == 20
    assert set(LEGAL_ACTIONS) <= set(_CELLS)


def _make_finding(
    conn: psycopg.Connection[dict[str, object]], classification: str, ref: str
) -> int:
    if classification == "ORPHANED":
        row = conn.execute(
            "SELECT ledger_attach_finding(NULL, 'refdest-c2', %s, 'ORPHANED', NULL, "
            "%s, 'sha256:0', 'sweep') AS fid",
            (ref, Jsonb({"probe_ids": [1]})),
        ).fetchone()
    else:
        effect_id = make_effect(conn)
        frontier = _HOME_FRONTIER[classification]
        assert frontier is not None
        make_execution_at(conn, effect_id, frontier)
        row = conn.execute(
            "SELECT ledger_attach_finding(%s, 'refdest-c2', NULL, %s, %s, %s, "
            "'sha256:0', 'reconciler') AS fid",
            (
                effect_id,
                classification,
                1 if classification == "DUPLICATE" else None,
                Jsonb({"probe_ids": [1]}),
            ),
        ).fetchone()
    assert row is not None
    return int(row["fid"])  # type: ignore[arg-type]


def _resolve(
    conn: psycopg.Connection[dict[str, object]],
    finding_id: int,
    from_status: str,
    to_status: str,
    actor: str = "human",
) -> None:
    conn.execute(
        "SELECT ledger_resolve(%s, %s, %s, %s, %s)",
        (finding_id, from_status, to_status, actor, Jsonb({"note": "matrix"})),
    )


@pytest.mark.parametrize(
    ("classification", "action"), _CELLS, ids=[f"{c}x{a}" for c, a in _CELLS]
)
def test_resolution_cell(
    classification: str, action: str, fresh_db: DBHandles
) -> None:
    legal = (classification, action) in LEGAL_ACTIONS
    with admin_conn(fresh_db.admin_dsn) as conn:
        finding_id = _make_finding(conn, classification, f"dest_{action.lower()}")
        if classification == "CONFIRMED_UNIQUE":
            # Auto-resolved and CLOSED at attach (§3.3): any manual action from
            # OPEN is stale — the auto path is the only legal one, and it ran.
            with pytest.raises(psycopg.Error) as excinfo:
                _resolve(conn, finding_id, "OPEN", action)
            assert excinfo.value.sqlstate == "DT002"
            chain = conn.execute(
                "SELECT to_status FROM finding_resolutions WHERE finding_id = %s "
                "ORDER BY resolution_seq",
                (finding_id,),
            ).fetchall()
            assert [r["to_status"] for r in chain] == ["ACCEPTED_AS_IS", "CLOSED"]
            return
        if legal:
            _resolve(conn, finding_id, "OPEN", action)
            row = conn.execute(
                "SELECT to_status FROM finding_resolutions WHERE finding_id = %s "
                "ORDER BY resolution_seq DESC LIMIT 1",
                (finding_id,),
            ).fetchone()
            assert row is not None and row["to_status"] == action
            if action != "ESCALATED_HUMAN":
                _resolve(conn, finding_id, action, "CLOSED")
        else:
            before = conn.execute(
                "SELECT count(*) AS n FROM finding_resolutions"
            ).fetchone()
            with pytest.raises(psycopg.Error) as excinfo:
                _resolve(conn, finding_id, "OPEN", action)
            assert excinfo.value.sqlstate == "DT004", (
                f"{classification}×{action}: expected DT004, got "
                f"{excinfo.value.sqlstate}"
            )
            after = conn.execute(
                "SELECT count(*) AS n FROM finding_resolutions"
            ).fetchone()
            assert before is not None and after is not None
            assert after["n"] == before["n"]
            # Park it legally so the fresh_db auditor sees a coherent chain.
            _resolve(conn, finding_id, "OPEN", "ESCALATED_HUMAN")


def test_duplicate_redispatch_illegal_even_after_escalation(
    fresh_db: DBHandles,
) -> None:
    """REDISPATCHED on a DUPLICATE is ILLEGAL, always — redispatching a
    duplicate manufactures more (§3.3). The escalation route does not open it."""
    with admin_conn(fresh_db.admin_dsn) as conn:
        finding_id = _make_finding(conn, "DUPLICATE", "dest_esc")
        _resolve(conn, finding_id, "OPEN", "ESCALATED_HUMAN")
        with pytest.raises(psycopg.Error) as excinfo:
            _resolve(conn, finding_id, "ESCALATED_HUMAN", "REDISPATCHED")
        assert excinfo.value.sqlstate == "DT004"
        _resolve(conn, finding_id, "ESCALATED_HUMAN", "ACCEPTED_AS_IS")
        _resolve(conn, finding_id, "ACCEPTED_AS_IS", "CLOSED")


def test_escalated_human_reroutes_to_action_then_closes(fresh_db: DBHandles) -> None:
    with admin_conn(fresh_db.admin_dsn) as conn:
        finding_id = _make_finding(conn, "LOST", "dest_lost_esc")
        _resolve(conn, finding_id, "OPEN", "ESCALATED_HUMAN")
        _resolve(conn, finding_id, "ESCALATED_HUMAN", "REDISPATCHED")
        _resolve(conn, finding_id, "REDISPATCHED", "CLOSED")
        chain = conn.execute(
            "SELECT from_status, to_status FROM finding_resolutions "
            "WHERE finding_id = %s ORDER BY resolution_seq",
            (finding_id,),
        ).fetchall()
        assert [(r["from_status"], r["to_status"]) for r in chain] == [
            ("OPEN", "ESCALATED_HUMAN"),
            ("ESCALATED_HUMAN", "REDISPATCHED"),
            ("REDISPATCHED", "CLOSED"),
        ]


def test_open_to_closed_directly_is_illegal(fresh_db: DBHandles) -> None:
    with admin_conn(fresh_db.admin_dsn) as conn:
        finding_id = _make_finding(conn, "LOST", "dest_lost_direct")
        with pytest.raises(psycopg.Error) as excinfo:
            _resolve(conn, finding_id, "OPEN", "CLOSED")
        assert excinfo.value.sqlstate == "DT004"
        _resolve(conn, finding_id, "OPEN", "ESCALATED_HUMAN")


def test_stale_from_status_first_write_wins(fresh_db: DBHandles) -> None:
    """Concurrent resolve arbitration: UNIQUE (finding_id, from_status) +
    frontier check ⇒ the second writer with a stale from_status fails typed."""
    with admin_conn(fresh_db.admin_dsn) as conn:
        finding_id = _make_finding(conn, "LOST", "dest_lost_race")
        _resolve(conn, finding_id, "OPEN", "ACCEPTED_AS_IS")
        with pytest.raises(psycopg.Error) as excinfo:
            _resolve(conn, finding_id, "OPEN", "ESCALATED_HUMAN")
        assert excinfo.value.sqlstate == "DT002"
        _resolve(conn, finding_id, "ACCEPTED_AS_IS", "CLOSED")
