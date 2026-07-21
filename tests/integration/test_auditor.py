"""Auditor self-tests (testing.md §3.5): the auditor is verified against
hand-built corrupt ledgers — it must FAIL on each seeded violation, so it
cannot silently rot into a rubber stamp. Corruption is seeded as the superuser
(direct inserts bypass the locked functions; trigger drops simulate tampering).
"""

from __future__ import annotations

import pytest
from psycopg.types.json import Jsonb

from irrevon.ledger.auditor import audit
from tests.integration.conftest import DBHandles
from tests.integration.driver import admin_conn, make_effect, make_execution_at

pytestmark = pytest.mark.integration


def _rules(dsn: str) -> set[str]:
    return {v.rule for v in audit(dsn)}


def test_clean_ledger_has_no_violations(fresh_db_unaudited: DBHandles) -> None:
    with admin_conn(fresh_db_unaudited.admin_dsn) as conn:
        effect_id = make_effect(conn)
        make_execution_at(conn, effect_id, "SETTLED_COMMITTED")
    assert audit(fresh_db_unaudited.admin_dsn) == []


def test_detects_illegal_edge(fresh_db_unaudited: DBHandles) -> None:
    with admin_conn(fresh_db_unaudited.admin_dsn) as conn:
        effect_id = make_effect(conn)
        execution_id = make_execution_at(conn, effect_id, "PERSISTED")
        conn.execute(
            "INSERT INTO effect_transitions (execution_id, from_state, to_state, "
            "cause, actor, evidence) VALUES (%s, 'PERSISTED', 'SETTLED_COMMITTED', "
            "'receipt_ok', 'dispatcher', %s)",
            (execution_id, Jsonb({})),
        )
    assert "state_legality" in _rules(fresh_db_unaudited.admin_dsn)


def test_detects_contiguity_gap(fresh_db_unaudited: DBHandles) -> None:
    with admin_conn(fresh_db_unaudited.admin_dsn) as conn:
        effect_id = make_effect(conn)
        execution_id = make_execution_at(conn, effect_id, "INTENDED")
        # Legal edge shape, but from_state skips the actual frontier (INTENDED).
        conn.execute(
            "INSERT INTO effect_transitions (execution_id, from_state, to_state, "
            "cause, actor, evidence) VALUES (%s, 'DISPATCHED', 'AMBIGUOUS', "
            "'receipt_lost', 'dispatcher', %s)",
            (execution_id, Jsonb({})),
        )
    assert "contiguity" in _rules(fresh_db_unaudited.admin_dsn)


def test_detects_transition_after_terminal(fresh_db_unaudited: DBHandles) -> None:
    with admin_conn(fresh_db_unaudited.admin_dsn) as conn:
        effect_id = make_effect(conn)
        execution_id = make_execution_at(conn, effect_id, "SETTLED_COMMITTED")
        conn.execute(
            "INSERT INTO effect_transitions (execution_id, from_state, to_state, "
            "cause, actor, evidence) VALUES (%s, 'AMBIGUOUS', 'SETTLED_FAILED', "
            "'reconciled_absent', 'reconciler', %s)",
            (execution_id, Jsonb({"probe_ids": [1]})),
        )
    assert "terminality" in _rules(fresh_db_unaudited.admin_dsn)


def test_detects_ambiguous_without_receipt(fresh_db_unaudited: DBHandles) -> None:
    with admin_conn(fresh_db_unaudited.admin_dsn) as conn:
        effect_id = make_effect(conn)
        execution_id = make_execution_at(conn, effect_id, "DISPATCHED")
        conn.execute(
            "INSERT INTO effect_transitions (execution_id, from_state, to_state, "
            "cause, actor, evidence) VALUES (%s, 'DISPATCHED', 'AMBIGUOUS', "
            "'receipt_lost', 'dispatcher', %s)",
            (execution_id, Jsonb({})),
        )
    assert "ambiguous_evidence" in _rules(fresh_db_unaudited.admin_dsn)


def test_detects_unjustified_ambiguous_exit(fresh_db_unaudited: DBHandles) -> None:
    """'Silently resolved' is structurally detectable (master doc §12.1 row 8):
    a settle out of AMBIGUOUS without justification evidence is a violation."""
    with admin_conn(fresh_db_unaudited.admin_dsn) as conn:
        effect_id = make_effect(conn)
        execution_id = make_execution_at(conn, effect_id, "AMBIGUOUS")
        conn.execute(
            "INSERT INTO effect_transitions (execution_id, from_state, to_state, "
            "cause, actor, evidence) VALUES (%s, 'AMBIGUOUS', 'SETTLED_COMMITTED', "
            "'reconciled_present', 'reconciler', %s)",
            (execution_id, Jsonb({"unrelated": "no probe reference"})),
        )
    assert "ambiguous_evidence" in _rules(fresh_db_unaudited.admin_dsn)


def test_detects_illegal_attachment(fresh_db_unaudited: DBHandles) -> None:
    with admin_conn(fresh_db_unaudited.admin_dsn) as conn:
        effect_id = make_effect(conn)
        make_execution_at(conn, effect_id, "PERSISTED")
        conn.execute(
            "INSERT INTO findings (effect_id, adapter_id, classification, evidence, "
            "evidence_digest, created_by) VALUES (%s, 'refdest-c2', 'LOST', %s, "
            "'sha256:0', 'reconciler')",
            (effect_id, Jsonb({})),
        )
    assert "classification" in _rules(fresh_db_unaudited.admin_dsn)


def test_detects_illegal_resolution_chain(fresh_db_unaudited: DBHandles) -> None:
    with admin_conn(fresh_db_unaudited.admin_dsn) as conn:
        effect_id = make_effect(conn)
        make_execution_at(conn, effect_id, "SETTLED_COMMITTED")
        row = conn.execute(
            "INSERT INTO findings (effect_id, adapter_id, classification, "
            "excess_effect_count, evidence, evidence_digest, created_by) "
            "VALUES (%s, 'refdest-c2', 'DUPLICATE', 1, %s, 'sha256:0', 'reconciler') "
            "RETURNING finding_id",
            (effect_id, Jsonb({})),
        ).fetchone()
        assert row is not None
        conn.execute(
            "INSERT INTO finding_resolutions (finding_id, from_status, to_status, "
            "evidence, actor) VALUES (%s, 'OPEN', 'REDISPATCHED', %s, 'human')",
            (row["finding_id"], Jsonb({})),
        )
    assert "resolution" in _rules(fresh_db_unaudited.admin_dsn)


def test_detects_dropped_append_only_trigger(fresh_db_unaudited: DBHandles) -> None:
    with admin_conn(fresh_db_unaudited.admin_dsn) as conn:
        conn.execute("DROP TRIGGER effect_records_append_only ON effect_records")
    assert "append_only" in _rules(fresh_db_unaudited.admin_dsn)


def test_detects_dispatched_without_gate_decision(
    fresh_db_unaudited: DBHandles,
) -> None:
    with admin_conn(fresh_db_unaudited.admin_dsn) as conn:
        effect_id = make_effect(conn)
        row = conn.execute(
            "INSERT INTO effect_executions (effect_id, step, operation_id, opened_by) "
            "VALUES (%s, 0, %s, 'register') RETURNING execution_id",
            (effect_id, f"{effect_id}:0"),
        ).fetchone()
        assert row is not None
        for f, t, c, a in [
            (None, "INTENDED", "register", "registrar"),
            ("INTENDED", "PERSISTED", "durable_write", "registrar"),
            ("PERSISTED", "DISPATCHED", "gate_allow", "gate"),
        ]:
            conn.execute(
                "INSERT INTO effect_transitions (execution_id, from_state, to_state, "
                "cause, actor, evidence) VALUES (%s, %s, %s, %s, %s, %s)",
                (row["execution_id"], f, t, c, a, Jsonb({})),
            )
    assert "gate" in _rules(fresh_db_unaudited.admin_dsn)


def test_detects_duplicate_without_excess(fresh_db_unaudited: DBHandles) -> None:
    with admin_conn(fresh_db_unaudited.admin_dsn) as conn:
        # Simulate schema tampering: drop the static CHECK (defense layer 2) so
        # the corrupt row can land; the auditor must still catch it.
        constraint = conn.execute(
            """
            SELECT conname FROM pg_constraint
            WHERE conrelid = 'findings'::regclass AND contype = 'c'
              AND pg_get_constraintdef(oid) ILIKE '%%excess%%'
            """
        ).fetchone()
        assert constraint is not None
        conn.execute(
            f'ALTER TABLE findings DROP CONSTRAINT "{constraint["conname"]}"'
        )
        effect_id = make_effect(conn)
        make_execution_at(conn, effect_id, "SETTLED_COMMITTED")
        conn.execute(
            "INSERT INTO findings (effect_id, adapter_id, classification, "
            "excess_effect_count, evidence, evidence_digest, created_by) "
            "VALUES (%s, 'refdest-c2', 'DUPLICATE', NULL, %s, 'sha256:0', 'reconciler')",
            (effect_id, Jsonb({})),
        )
    assert "classification" in _rules(fresh_db_unaudited.admin_dsn)
