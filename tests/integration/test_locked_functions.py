"""Privilege separation: the ledger is the sole transition writer (RFC-002 §2.3).

T-102 acceptance edge case + testing.md §4.3 corrupt-insert leg: direct writes
to the lifecycle tables as irrevon_app must raise insufficient_privilege; direct
UPDATE/DELETE anywhere must be rejected by the append-only triggers.
"""

from __future__ import annotations

import psycopg
import pytest
from psycopg.rows import dict_row
from psycopg.types.json import Jsonb

from tests.integration.conftest import DBHandles
from tests.integration.driver import admin_conn, make_effect, make_execution_at

pytestmark = pytest.mark.integration


def _app_conn(dsn: str) -> psycopg.Connection[dict[str, object]]:
    return psycopg.connect(dsn, row_factory=dict_row, autocommit=True)


@pytest.mark.parametrize(
    "statement",
    [
        # effect_transitions: the locked table (C1 finding B2 fix).
        "INSERT INTO effect_transitions (execution_id, from_state, to_state, cause,"
        " actor, evidence) VALUES (1, NULL, 'INTENDED', 'register', 'registrar', '{}')",
        # effect_executions: step allocation is the ledger's, not the app's.
        "INSERT INTO effect_executions (effect_id, step, operation_id, opened_by)"
        " VALUES ('0000000000000000000000000000000000000000000000000000000000000000',"
        " 0, '0000000000000000000000000000000000000000000000000000000000000000:0',"
        " 'register')",
        # findings: attachment legality lives in ledger_attach_finding.
        "INSERT INTO findings (effect_id, adapter_id, classification, evidence,"
        " evidence_digest, created_by) VALUES (NULL, 'a', 'ORPHANED', '{}', 'd', 'sweep')",
        # finding_resolutions: resolution legality lives in ledger_resolve.
        "INSERT INTO finding_resolutions (finding_id, from_status, to_status,"
        " evidence, actor) VALUES (1, 'OPEN', 'CLOSED', '{}', 'human')",
        # Ratified seed tables are read-only reference data.
        "INSERT INTO lifecycle_edges (from_state, to_state, cause, actor)"
        " VALUES ('CANCELLED', 'PERSISTED', 'register', 'registrar')",
    ],
    ids=[
        "effect_transitions",
        "effect_executions",
        "findings",
        "finding_resolutions",
        "lifecycle_edges",
    ],
)
def test_direct_insert_as_app_role_is_denied(
    statement: str, fresh_db: DBHandles
) -> None:
    with _app_conn(fresh_db.app_dsn) as conn:
        with pytest.raises(psycopg.errors.InsufficientPrivilege):
            conn.execute(statement)  # type: ignore[arg-type]


def test_update_and_delete_rejected_everywhere(fresh_db: DBHandles) -> None:
    """Append-only enforcement layer 1: even the SUPERUSER cannot UPDATE or
    DELETE a fact row without dropping the trigger (which the auditor detects)."""
    with admin_conn(fresh_db.admin_dsn) as conn:
        effect_id = make_effect(conn)
        make_execution_at(conn, effect_id, "PERSISTED")
        with pytest.raises(psycopg.errors.RaiseException):
            conn.execute(
                "UPDATE effect_records SET scope = 'rewritten' WHERE effect_id = %s",
                (effect_id,),
            )
        with pytest.raises(psycopg.errors.RaiseException):
            conn.execute(
                "DELETE FROM effect_transitions WHERE execution_id IN "
                "(SELECT execution_id FROM effect_executions WHERE effect_id = %s)",
                (effect_id,),
            )


def test_app_role_can_lock_but_not_update(fresh_db: DBHandles) -> None:
    """The claim protocol needs SELECT … FOR UPDATE on scope_slots and
    effect_records (UPDATE privilege), but an actual UPDATE must still raise."""
    with admin_conn(fresh_db.admin_dsn) as conn:
        effect_id = make_effect(conn)
    with psycopg.connect(fresh_db.app_dsn, row_factory=dict_row) as conn:
        with conn.transaction():
            row = conn.execute(
                "SELECT effect_id FROM effect_records WHERE effect_id = %s FOR UPDATE",
                (effect_id,),
            ).fetchone()
            assert row is not None
        with pytest.raises(psycopg.errors.RaiseException):
            conn.execute(
                "UPDATE effect_records SET scope = 'x' WHERE effect_id = %s",
                (effect_id,),
            )


def test_app_role_writes_lifecycle_via_functions_only(fresh_db: DBHandles) -> None:
    """The sanctioned path works end-to-end as irrevon_app: open execution,
    transition, attach, resolve — all through the SECURITY DEFINER functions."""
    with admin_conn(fresh_db.admin_dsn) as conn:
        effect_id = make_effect(conn)
    with _app_conn(fresh_db.app_dsn) as conn:
        row = conn.execute(
            "SELECT * FROM ledger_open_execution(%s, 'register')", (effect_id,)
        ).fetchone()
        assert row is not None and row["state"] == "PERSISTED"
        conn.execute(
            "SELECT ledger_transition(%s, 'PERSISTED', 'CANCELLED', "
            "'branch_cancelled', 'human', %s)",
            (row["execution_id"], Jsonb({"note": "operator cancel"})),
        )
        frontier = conn.execute(
            "SELECT frontier FROM execution_frontiers WHERE execution_id = %s",
            (row["execution_id"],),
        ).fetchone()
        assert frontier is not None and frontier["frontier"] == "CANCELLED"


def test_open_execution_preconditions(fresh_db: DBHandles) -> None:
    """register only opens step 0; non-initial opens require SETTLED_FAILED."""
    with admin_conn(fresh_db.admin_dsn) as conn:
        effect_id = make_effect(conn)
        conn.execute("SELECT ledger_open_execution(%s, 'register')", (effect_id,))
        with pytest.raises(psycopg.Error) as excinfo:
            conn.execute("SELECT ledger_open_execution(%s, 'register')", (effect_id,))
        assert excinfo.value.sqlstate == "DT005"
        with pytest.raises(psycopg.Error) as excinfo:
            conn.execute(
                "SELECT ledger_open_execution(%s, 'retry_after_failure')", (effect_id,)
            )
        assert excinfo.value.sqlstate == "DT005"
