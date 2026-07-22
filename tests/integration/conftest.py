"""Integration-test harness: template-database-per-test (testing.md §3.1).

One local Postgres 17 (docker-compose.yml, digest-pinned) hosts a template
database built once per migration-set hash; every test clones it (~10-50 ms),
so tests get real commits, real WAL, real row + advisory locks, and total
isolation — transaction-rollback isolation is disqualified because it mocks
durability (testing.md §3.1). Mocks never replace Postgres transactional
behavior.

The ledger auditor runs as a post-condition after EVERY test that uses
``fresh_db`` (testing.md §3.5); tests that deliberately corrupt the ledger use
``fresh_db_unaudited``.
"""

from __future__ import annotations

import hashlib
import os
import uuid
from collections.abc import Iterator
from dataclasses import dataclass

import psycopg
import pytest
from psycopg import sql

from irrevon.ledger.auditor import audit
from irrevon.ledger.db import apply_migrations, migrations_dir

ADMIN_DSN = os.environ.get(
    "IRREVON_TEST_ADMIN_DSN", "postgresql://postgres@127.0.0.1:54329/postgres"
)
_TEMPLATE_LOCK = 0x_DE7E_2026


@dataclass(frozen=True)
class DBHandles:
    name: str
    admin_dsn: str  # superuser — oracle SQL, corrupt-ledger seeding
    app_dsn: str  # irrevon_app — what the engine itself is allowed to do


def _dsn_for(dbname: str, user: str | None = None) -> str:
    kwargs: dict[str, str] = {"dbname": dbname}
    if user is not None:
        kwargs["user"] = user
    return psycopg.conninfo.make_conninfo(ADMIN_DSN, **kwargs)  # type: ignore[arg-type]


@pytest.fixture(scope="session")
def template_db() -> str:
    """Build (once per migration-set hash) the migrated template database and
    keep ZERO connections to it (CREATE DATABASE … TEMPLATE requirement)."""
    digest = hashlib.sha256()
    for path in sorted(migrations_dir().glob("*.sql")):
        digest.update(path.name.encode())
        digest.update(path.read_bytes())
    name = f"irrevon_tpl_{digest.hexdigest()[:12]}"
    try:
        admin = psycopg.connect(ADMIN_DSN, autocommit=True)
    except psycopg.OperationalError as err:  # pragma: no cover
        pytest.fail(
            f"integration Postgres unreachable at {ADMIN_DSN} — run "
            f"`make py-db-up` (docker-compose.yml) first: {err}"
        )
    with admin:
        admin.execute("SELECT pg_advisory_lock(%s)", (_TEMPLATE_LOCK,))
        try:
            exists = admin.execute(
                "SELECT 1 FROM pg_database WHERE datname = %s", (name,)
            ).fetchone()
            if exists is None:
                admin.execute(
                    sql.SQL("CREATE DATABASE {}").format(sql.Identifier(name))
                )
                apply_migrations(_dsn_for(name))
                admin.execute(
                    "UPDATE pg_database SET datistemplate = true WHERE datname = %s",
                    (name,),
                )
        finally:
            admin.execute("SELECT pg_advisory_unlock(%s)", (_TEMPLATE_LOCK,))
    return name


def _clone(template: str) -> DBHandles:
    name = f"irrevon_test_{uuid.uuid4().hex[:12]}"
    with psycopg.connect(ADMIN_DSN, autocommit=True) as admin:
        admin.execute(
            sql.SQL("CREATE DATABASE {} TEMPLATE {}").format(
                sql.Identifier(name), sql.Identifier(template)
            )
        )
    return DBHandles(
        name=name, admin_dsn=_dsn_for(name), app_dsn=_dsn_for(name, "irrevon_app")
    )


def _drop(name: str) -> None:
    with psycopg.connect(ADMIN_DSN, autocommit=True) as admin:
        admin.execute(
            """
            SELECT pg_terminate_backend(pid) FROM pg_stat_activity
            WHERE datname = %s AND pid <> pg_backend_pid()
            """,
            (name,),
        )
        admin.execute(sql.SQL("DROP DATABASE {}").format(sql.Identifier(name)))


@pytest.fixture
def fresh_db(template_db: str) -> Iterator[DBHandles]:
    """A pristine migrated database; the ledger auditor asserts the global
    invariants after the test body (the standing §3.5 post-condition)."""
    handles = _clone(template_db)
    violations = None
    try:
        yield handles
        violations = audit(handles.admin_dsn)
    finally:
        _drop(handles.name)
    assert violations == [], f"ledger auditor violations: {violations}"


@pytest.fixture
def fresh_db_unaudited(template_db: str) -> Iterator[DBHandles]:
    """For tests that deliberately corrupt the ledger (auditor self-tests)."""
    handles = _clone(template_db)
    try:
        yield handles
    finally:
        _drop(handles.name)
