"""Connection helpers, typed-error mapping, and the plain-SQL migration runner.

The ledger is the only module with SQL (RFC-002 §14). Migration runner choice
per ADR-0022 (proposed): a minimal in-package runner over language-neutral
``migrations/*.sql`` files, applied in lexical order with a sha256 journal.
"""

from __future__ import annotations

import hashlib
from collections.abc import Iterator
from contextlib import contextmanager
from pathlib import Path
from typing import Any

import psycopg
from psycopg.rows import dict_row

from irrevon.errors import (
    IllegalState,
    IrrevonError,
    ResolutionInvalid,
    StorageUnavailable,
)

__all__ = ["apply_migrations", "connect", "migrations_dir", "translated_errors"]

# Custom SQLSTATEs raised by the locked ledger functions (migrations/0003).
_SQLSTATE_MAP: dict[str, type[IrrevonError]] = {
    "DT001": IllegalState,  # illegal lifecycle edge
    "DT002": IllegalState,  # stale expected_from / lost race
    "DT003": IllegalState,  # illegal classification attachment
    "DT004": ResolutionInvalid,
    "DT005": IllegalState,  # precondition violation
}


def connect(dsn: str) -> psycopg.Connection[dict[str, Any]]:
    """Open a non-autocommit connection with dict rows; maps unreachability to
    the retryable ``storage_unavailable`` error."""
    try:
        return psycopg.connect(dsn, row_factory=dict_row)
    except psycopg.OperationalError as err:
        raise StorageUnavailable(f"ledger unreachable: {err}") from err


@contextmanager
def translated_errors() -> Iterator[None]:
    """Translate ledger-function SQLSTATEs into the typed error hierarchy."""
    try:
        yield
    except psycopg.errors.RaiseException as err:
        # plpgsql RAISE without a custom code lands here (append-only trigger).
        raise IllegalState(str(err.diag.message_primary or err)) from err
    except psycopg.Error as err:
        sqlstate = err.sqlstate or ""
        mapped = _SQLSTATE_MAP.get(sqlstate)
        if mapped is not None:
            raise mapped(str(err.diag.message_primary or err)) from err
        raise


def migrations_dir() -> Path:
    """Locate the canonical ``migrations/`` directory (repo or packaged copy)."""
    packaged = Path(__file__).resolve().parent.parent / "_migrations"
    if packaged.is_dir() and any(packaged.glob("*.sql")):
        return packaged
    for parent in Path(__file__).resolve().parents:
        candidate = parent / "migrations"
        if candidate.is_dir() and any(candidate.glob("*.sql")):
            return candidate
    raise FileNotFoundError("migrations/ directory not found")


_JOURNAL_DDL = """
CREATE TABLE IF NOT EXISTS irrevon_schema_migrations (
  filename   text PRIMARY KEY,
  sha256     text NOT NULL,
  applied_at timestamptz NOT NULL DEFAULT now()
)
"""


def apply_migrations(dsn: str, directory: Path | None = None) -> list[str]:
    """Apply pending ``*.sql`` migrations in lexical order, one transaction
    each, journaled by content hash. A journaled file whose content changed is
    an integrity error, never silently re-run (append-only discipline)."""
    directory = directory or migrations_dir()
    applied: list[str] = []
    with connect(dsn) as conn:
        conn.execute(_JOURNAL_DDL)
        conn.commit()
        journal = {
            row["filename"]: row["sha256"]
            for row in conn.execute(
                "SELECT filename, sha256 FROM irrevon_schema_migrations"
            ).fetchall()
        }
        for path in sorted(directory.glob("*.sql")):
            content = path.read_text(encoding="utf-8")
            digest = hashlib.sha256(content.encode("utf-8")).hexdigest()
            if path.name in journal:
                if journal[path.name] != digest:
                    raise RuntimeError(
                        f"migration {path.name} changed after being applied "
                        f"(journaled {journal[path.name][:12]}…, on disk {digest[:12]}…); "
                        "migrations are append-only — add a new file instead"
                    )
                continue
            conn.execute(content)
            conn.execute(
                "INSERT INTO irrevon_schema_migrations (filename, sha256) VALUES (%s, %s)",
                (path.name, digest),
            )
            conn.commit()
            applied.append(path.name)
    return applied
