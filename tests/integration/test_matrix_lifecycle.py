"""Exhaustive dimension-A state-matrix tests (RFC-002 §3.1; testing.md §4.3).

Conformance: master doc §12.1 row 3 — "Illegal lifecycle × classification
combinations rejected (§7.1, ADR-004)" (M3), dimension-A leg. Every one of the
56 (from, to) ordered cells (incl. genesis) is driven against the REAL locked
transition writer on real Postgres: legal cells succeed only with their ratified
(cause, actor) guard; illegal cells are rejected with a typed error and append
NO row. The oracle is the explicit fixture table (fixtures/lifecycle-matrix.json,
transcribed from the ratified RFC table), not the code.
"""

from __future__ import annotations

import json
from pathlib import Path

import psycopg
import pytest
from psycopg.types.json import Jsonb

from irrevon.statetable import (
    LEGAL_STATE_PAIRS,
    LIFECYCLE_EDGES,
    LIFECYCLE_STATES,
)
from tests.integration.conftest import DBHandles
from tests.integration.driver import (
    add_dispatch_evidence,
    add_receipt,
    admin_conn,
    make_effect,
    make_execution_at,
    transition_count,
)

pytestmark = pytest.mark.integration

FIXTURE = json.loads(
    (Path(__file__).parent / "fixtures" / "lifecycle-matrix.json").read_text()
)
CELLS: dict[str, str] = FIXTURE["cells"]

# A representative ratified (cause, actor) per legal (from, to) pair; illegal
# pairs are probed with a fallback pair — the edge must reject regardless.
_LEGAL_CAUSE_ACTOR: dict[tuple[str | None, str], tuple[str, str]] = {}
for _f, _t, _c, _a in sorted(
    LIFECYCLE_EDGES, key=lambda e: (str(e[0]), e[1], e[2], e[3])
):
    _LEGAL_CAUSE_ACTOR.setdefault((_f, _t), (_c, _a))


def test_meta_every_cell_has_explicit_expectation() -> None:
    """The meta-test (testing.md §4.3): 'undefined' is unrepresentable — the
    fixture must carry an explicit LEGAL/ILLEGAL verdict for every cell."""
    expected_keys = {
        f"{f}->{t}" for f in ("GENESIS", *LIFECYCLE_STATES) for t in LIFECYCLE_STATES
    }
    assert set(CELLS) == expected_keys, "fixture must cover every cell exactly once"
    assert all(v in ("LEGAL", "ILLEGAL") for v in CELLS.values())


def test_meta_fixture_matches_ratified_table() -> None:
    """Generated-from discipline: the fixture's legal set IS the §3.1 table."""
    fixture_legal = {
        (None if k.split("->")[0] == "GENESIS" else k.split("->")[0], k.split("->")[1])
        for k, v in CELLS.items()
        if v == "LEGAL"
    }
    assert fixture_legal == set(LEGAL_STATE_PAIRS)


@pytest.mark.parametrize("cell", sorted(CELLS), ids=lambda c: c)
def test_cell(cell: str, fresh_db: DBHandles) -> None:
    from_label, to_state = cell.split("->")
    from_state: str | None = None if from_label == "GENESIS" else from_label
    expectation = CELLS[cell]

    with admin_conn(fresh_db.admin_dsn) as conn:
        effect_id = make_effect(conn)
        if from_state is None:
            row = conn.execute(
                """
                INSERT INTO effect_executions (effect_id, step, operation_id, opened_by)
                VALUES (%s, 0, %s, 'register') RETURNING execution_id
                """,
                (effect_id, f"{effect_id}:0"),
            ).fetchone()
            assert row is not None
            execution_id: int = row["execution_id"]
        else:
            execution_id = make_execution_at(conn, effect_id, from_state)

        cause, actor = _LEGAL_CAUSE_ACTOR.get(
            (from_state, to_state), ("register", "registrar")
        )
        evidence = Jsonb({"matrix_cell": cell, "probe_ids": [0]})
        before = transition_count(conn)

        if expectation == "LEGAL":
            conn.execute(
                "SELECT ledger_transition(%s, %s, %s, %s, %s, %s)",
                (execution_id, from_state, to_state, cause, actor, evidence),
            )
            assert transition_count(conn) == before + 1
            frontier = conn.execute(
                "SELECT frontier FROM execution_frontiers WHERE execution_id = %s",
                (execution_id,),
            ).fetchone()
            assert frontier is not None and frontier["frontier"] == to_state
            # Patch-up evidence so the standing auditor post-condition holds for
            # the state the execution ends in (decision/attempt/receipt rows).
            if to_state == "INTENDED":
                conn.execute(
                    "SELECT ledger_transition(%s, 'INTENDED', 'PERSISTED', "
                    "'durable_write', 'registrar', %s)",
                    (execution_id, Jsonb({"matrix_cell": cell})),
                )
            elif to_state == "DISPATCHED":
                add_dispatch_evidence(conn, effect_id, execution_id)
            elif to_state == "AMBIGUOUS":
                add_receipt(conn, execution_id, "LOST")
        else:
            with pytest.raises(psycopg.Error) as excinfo:
                conn.execute(
                    "SELECT ledger_transition(%s, %s, %s, %s, %s, %s)",
                    (execution_id, from_state, to_state, cause, actor, evidence),
                )
            # Typed rejection: illegal edge (DT001); nothing appended.
            assert excinfo.value.sqlstate == "DT001", (
                f"cell {cell}: expected DT001, got {excinfo.value.sqlstate}"
            )
            assert transition_count(conn) == before


def test_legal_edge_with_wrong_cause_rejected(fresh_db: DBHandles) -> None:
    """Cause is part of edge legality: a legal (from, to) with a wrong cause
    must reject (DISPATCHED→SETTLED_COMMITTED via receipt_failed)."""
    with admin_conn(fresh_db.admin_dsn) as conn:
        effect_id = make_effect(conn)
        execution_id = make_execution_at(conn, effect_id, "DISPATCHED")
        add_receipt(conn, execution_id, "OK")
        before = transition_count(conn)
        with pytest.raises(psycopg.Error) as excinfo:
            conn.execute(
                "SELECT ledger_transition(%s, 'DISPATCHED', 'SETTLED_COMMITTED', "
                "'receipt_failed', 'dispatcher', %s)",
                (execution_id, Jsonb({})),
            )
        assert excinfo.value.sqlstate == "DT001"
        assert transition_count(conn) == before
        conn.execute(
            "SELECT ledger_transition(%s, 'DISPATCHED', 'SETTLED_COMMITTED', "
            "'receipt_ok', 'dispatcher', %s)",
            (execution_id, Jsonb({"receipt_id": 1})),
        )


def test_legal_edge_with_wrong_actor_rejected(fresh_db: DBHandles) -> None:
    """Actor is part of edge legality: DISPATCHED→SETTLED_COMMITTED is a
    dispatcher edge; the reconciler may not take it."""
    with admin_conn(fresh_db.admin_dsn) as conn:
        effect_id = make_effect(conn)
        execution_id = make_execution_at(conn, effect_id, "DISPATCHED")
        before = transition_count(conn)
        with pytest.raises(psycopg.Error) as excinfo:
            conn.execute(
                "SELECT ledger_transition(%s, 'DISPATCHED', 'SETTLED_COMMITTED', "
                "'receipt_ok', 'reconciler', %s)",
                (execution_id, Jsonb({})),
            )
        assert excinfo.value.sqlstate == "DT001"
        assert transition_count(conn) == before
        add_receipt(conn, execution_id, "LOST")
        conn.execute(
            "SELECT ledger_transition(%s, 'DISPATCHED', 'AMBIGUOUS', "
            "'receipt_lost', 'dispatcher', %s)",
            (execution_id, Jsonb({"receipt_id": 1})),
        )
        conn.execute(
            "SELECT ledger_transition(%s, 'AMBIGUOUS', 'SETTLED_COMMITTED', "
            "'reconciled_present', 'reconciler', %s)",
            (execution_id, Jsonb({"probe_ids": [1]})),
        )


def test_stale_expected_from_writes_nothing(fresh_db: DBHandles) -> None:
    """T-102 acceptance edge case: ledger_transition with a stale expected_from
    raises (DT002) and writes nothing."""
    with admin_conn(fresh_db.admin_dsn) as conn:
        effect_id = make_effect(conn)
        execution_id = make_execution_at(conn, effect_id, "DISPATCHED")
        before = transition_count(conn)
        with pytest.raises(psycopg.Error) as excinfo:
            conn.execute(
                "SELECT ledger_transition(%s, 'PERSISTED', 'DISPATCHED', "
                "'gate_allow', 'gate', %s)",
                (execution_id, Jsonb({})),
            )
        assert excinfo.value.sqlstate == "DT002"
        assert transition_count(conn) == before
        add_receipt(conn, execution_id, "OK")
        conn.execute(
            "SELECT ledger_transition(%s, 'DISPATCHED', 'SETTLED_COMMITTED', "
            "'receipt_ok', 'dispatcher', %s)",
            (execution_id, Jsonb({"receipt_id": 1})),
        )
