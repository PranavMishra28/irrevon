"""Read-only layers 2 (irrevon_read privileges, migration 0005) and 3 (session
read-only) — TESTED, not asserted (integration tier).

Layer 3 is proven by attempting a write in a serve session (rejected as a
read-only transaction). Layer 2 is proven INDEPENDENTLY by explicitly lifting
the session guard (``SET TRANSACTION READ WRITE``) and showing the privilege
layer still refuses; plus a grants audit and the no-EXECUTE proof on every
locked ledger transition function."""

from __future__ import annotations

import psycopg
import pytest
from psycopg.rows import dict_row

from irrevon.serve import READ_ROLE, read_connection, read_dsn
from tests.serve.conftest import DBHandles

pytestmark = pytest.mark.integration

_LOCKED_FUNCTIONS = (
    "ledger_open_execution(text, text)",
    "ledger_transition(bigint, text, text, text, text, jsonb)",
    "ledger_attach_finding(text, text, text, text, integer, jsonb, text, text)",
    "ledger_resolve(bigint, text, text, text, jsonb)",
)


def test_serve_sessions_default_to_read_only(fresh_db: DBHandles) -> None:
    with read_connection(fresh_db.admin_dsn) as conn:
        row = conn.execute("SHOW default_transaction_read_only").fetchone()
        assert row is not None and row["default_transaction_read_only"] == "on"
        who = conn.execute("SELECT current_user AS u").fetchone()
        assert who is not None and who["u"] == READ_ROLE


def test_layer3_session_rejects_writes(fresh_db: DBHandles) -> None:
    with read_connection(fresh_db.admin_dsn) as conn:
        with pytest.raises(psycopg.errors.ReadOnlySqlTransaction):
            conn.execute(
                "INSERT INTO authorities (authority_ref, scope, stamped_at)"
                " VALUES ('x', 's/p', now())"
            )


def test_layer2_privileges_reject_writes_even_read_write(
    fresh_db: DBHandles,
) -> None:
    """Even with the session guard explicitly lifted, the SELECT-only role
    cannot write — the grep-able escape hatch buys an attacker nothing."""
    with read_connection(fresh_db.admin_dsn) as conn:
        # psycopg opens the transaction implicitly; this must be its first
        # statement to lift the session-level read-only default (layer 3).
        conn.execute("SET TRANSACTION READ WRITE")
        with pytest.raises(psycopg.errors.InsufficientPrivilege):
            conn.execute(
                "INSERT INTO authorities (authority_ref, scope, stamped_at)"
                " VALUES ('x', 's/p', now())"
            )


def test_read_role_has_no_execute_on_locked_functions(
    fresh_db: DBHandles,
) -> None:
    with psycopg.connect(fresh_db.admin_dsn, row_factory=dict_row) as admin:
        for signature in _LOCKED_FUNCTIONS:
            row = admin.execute(
                "SELECT has_function_privilege(%s, %s, 'EXECUTE') AS can",
                (READ_ROLE, signature),
            ).fetchone()
            assert row is not None
            assert row["can"] is False, f"{READ_ROLE} can EXECUTE {signature}"


def test_grants_audit_select_only(fresh_db: DBHandles) -> None:
    """information_schema audit: zero non-SELECT table grants, zero sequence
    grants, for the read role — the migration's 'deliberately absent' list."""
    with psycopg.connect(fresh_db.admin_dsn, row_factory=dict_row) as admin:
        rows = admin.execute(
            """
            SELECT table_name, privilege_type
            FROM information_schema.role_table_grants
            WHERE grantee = %s AND privilege_type <> 'SELECT'
            """,
            (READ_ROLE,),
        ).fetchall()
        assert rows == [], f"non-SELECT grants exist: {rows}"
        seq = admin.execute(
            """
            SELECT count(*) AS n FROM information_schema.usage_privileges
            WHERE grantee = %s AND object_type = 'SEQUENCE'
            """,
            (READ_ROLE,),
        ).fetchone()
        assert seq is not None and int(seq["n"]) == 0


def test_read_role_can_select_everything_the_routes_need(
    fresh_db: DBHandles,
) -> None:
    tables = (
        "effect_records",
        "effect_frontiers",
        "effect_executions",
        "effect_transitions",
        "dispatch_receipts",
        "dispatch_attempts",
        "findings",
        "finding_resolutions",
        "gate_decisions",
        "status_probes",
        "authorities",
        "effect_authorities",
        "irrevon_schema_migrations",
    )
    with read_connection(fresh_db.admin_dsn) as conn:
        for table in tables:
            conn.execute(f"SELECT * FROM {table} LIMIT 1").fetchall()


def test_read_dsn_swaps_only_the_user(fresh_db: DBHandles) -> None:
    dsn = read_dsn(fresh_db.admin_dsn)
    assert f"user={READ_ROLE}" in dsn
    assert "default_transaction_read_only=on" in dsn
