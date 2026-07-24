"""Backup/restore evidence (docs/operations.md runbook, executed).

pg_dump the ledger mid-doubt (an AMBIGUOUS effect in flight), restore into a
fresh database, boot ONE worker — recovery replay must adjudicate against the
DESTINATION (the authority for what happened after the backup point), not the
backup. Runs the dump/restore inside the compose Postgres container so no
host client tooling is assumed."""

from __future__ import annotations

import subprocess
from datetime import UTC, datetime
from typing import Any

import pytest

from irrevon.adapters.base import declarations_dir, load_declaration
from irrevon.adapters.refdest import RefDest, RefdestAdapter
from irrevon.api import Engine
from irrevon.dispatcher import dispatch
from irrevon.ledger import Ledger
from tests.integration.conftest import DBHandles

pytestmark = pytest.mark.integration

C2_DECL = load_declaration(declarations_dir() / "refdest-c2.capability.json")


def _in_container(sql_or_cmd: list[str]) -> subprocess.CompletedProcess[bytes]:
    return subprocess.run(
        ["docker", "compose", "exec", "-T", "ledger-db-test", *sql_or_cmd],
        capture_output=True,
        timeout=120,
        check=False,
    )


def _dbname(dsn: str) -> str:
    """Works for both URL and key-value conninfo forms."""
    for token in dsn.split():
        if token.startswith("dbname="):
            return token.removeprefix("dbname=")
    from urllib.parse import urlparse

    return urlparse(dsn).path.lstrip("/")


def test_backup_restore_recovers_via_destination_readback(
    fresh_db: DBHandles,
) -> None:
    refdest = RefDest(seed=23, profile="C2")
    adapter = RefdestAdapter("refdest-c2", C2_DECL, instance=refdest)
    raw: dict[str, Any] = {
        "schema_version": "1",
        "stable_ids": {"order_id": "br-1"},
        "effect_type": "order.create",
        "effect_class": "IRREVERSIBLE",
        "scope": "backup/br-1",
        "adapter_id": "refdest-c2",
        "parameters": {"note": "backup-restore-test"},
        "authority_ref": "auth_br",
        "stamped_at": datetime.now(UTC).isoformat().replace("+00:00", "Z"),
    }
    with Ledger(fresh_db.app_dsn) as ledger:
        reg = ledger.register_intent(raw, adapter.declaration_digest())
        refdest.control_schedule(
            [{"match": {"op": "create"}, "fault": "DROP_RESPONSE_AFTER_COMMIT"}]
        )
        report = dispatch(ledger, adapter, reg.effect_id)
        assert report.lifecycle == "AMBIGUOUS"  # mid-doubt: the backup point
        effect_id = reg.effect_id

    source_db = _dbname(fresh_db.app_dsn)
    restored_db = f"{source_db}_restored"

    # Backup (plain-format dump inside the container; no host tooling).
    dump = _in_container(
        ["pg_dump", "-h", "127.0.0.1", "-p", "5432", "-U", "postgres",
         "--no-owner", source_db]
    )
    assert dump.returncode == 0, dump.stderr.decode()[:500]
    assert b"effect_records" in dump.stdout

    # Restore into a fresh database.
    for statement in (
        f'DROP DATABASE IF EXISTS "{restored_db}"',
        f'CREATE DATABASE "{restored_db}"',
    ):
        result = _in_container(
            ["psql", "-h", "127.0.0.1", "-p", "5432", "-U", "postgres", "-c", statement]
        )
        assert result.returncode == 0, result.stderr.decode()[:500]
    restore = subprocess.run(
        ["docker", "compose", "exec", "-T", "ledger-db-test",
         "psql", "-h", "127.0.0.1", "-p", "5432", "-U", "postgres",
         "-v", "ON_ERROR_STOP=1", "-d", restored_db],
        input=dump.stdout, capture_output=True, timeout=120, check=False,
    )
    assert restore.returncode == 0, restore.stderr.decode()[:500]

    try:
        # Boot ONE engine against the restore: recovery replay must query the
        # destination BEFORE any new work — and settle the mid-doubt record
        # from destination truth (the effect DID commit pre-backup).
        restored_dsn = fresh_db.app_dsn.replace(source_db, restored_db)
        engine = Engine(restored_dsn, {"refdest-c2": adapter})
        recovery = engine.boot()
        assert recovery.scanned == 1 and recovery.adjudicated == 1
        frontier = engine.ledger.effect_frontier(effect_id)["frontier"]
        assert frontier == "SETTLED_COMMITTED"
        classifications = [
            f["classification"] for f in engine.ledger.findings_for(effect_id)
        ]
        assert classifications == ["CONFIRMED_UNIQUE"]
        # Destination read-back, not the backup, was the authority: exactly
        # one destination effect exists (no re-dispatch on belief).
        assert len(refdest.control_state()) == 1
        engine.close()
    finally:
        _in_container(["psql", "-h", "127.0.0.1", "-p", "5432", "-U", "postgres", "-c",
                       f'DROP DATABASE IF EXISTS "{restored_db}"'])
