"""Security regressions for demo handoff and destructive-name bounds."""

from __future__ import annotations

import json

import psycopg
import pytest

from irrevon.cli import main
from irrevon.cli.config import Config
from irrevon.cli.demo import (
    _demo_migration_dsn,
    _display_demo_dsn,
    _reset_demo_database,
    run_demo,
)
from irrevon.errors import ConfigInvalid


def test_display_demo_dsn_never_contains_password() -> None:
    marker = "opaque-password-that-must-not-print"
    config = Config(
        path=None,
        dsn=psycopg.conninfo.make_conninfo(
            user="irrevon",
            password=marker,
            host="localhost",
            port=5432,
            dbname="irrevon",
        ),
    )
    shown = _display_demo_dsn(config, "irrevon_demo_s42")
    assert marker not in shown
    assert "password" not in shown
    assert "dbname=irrevon_demo_s42" in shown


def test_demo_requires_explicit_migration_authority_before_starting(
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    monkeypatch.delenv("IRREVON_MIGRATION_DSN", raising=False)

    rc = main(["demo", "--leg", "irrevon", "--jsonl"])

    captured = capsys.readouterr()
    assert rc == 1
    assert captured.out == ""
    envelope = json.loads(captured.err)
    assert envelope["error"] == {
        "code": "config_invalid",
        "message": (
            "the Irrevon demo requires IRREVON_MIGRATION_DSN for its disposable "
            "demo database; export it directly, or copy .env.example to .env "
            "and source .env as shown in the README quickstart"
        ),
        "retryable": False,
        "details": {},
    }


def test_invalid_demo_migration_dsn_never_echoes_its_value(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    marker = "not-valid-and-must-not-print"
    monkeypatch.setenv("IRREVON_MIGRATION_DSN", marker)

    with pytest.raises(ConfigInvalid) as raised:
        _demo_migration_dsn()

    assert str(raised.value) == (
        "IRREVON_MIGRATION_DSN is not valid PostgreSQL connection information"
    )
    assert marker not in str(raised.value)


def test_unusable_demo_migration_authority_has_sanitized_guidance(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    marker = "opaque-migration-password-that-must-not-print"
    migration_dsn = psycopg.conninfo.make_conninfo(
        user="postgres",
        password=marker,
        host="localhost",
        port=5432,
        dbname="irrevon",
    )

    def unavailable(*args: object, **kwargs: object) -> object:
        raise psycopg.OperationalError(f"synthetic connection failure: {marker}")

    monkeypatch.setattr(psycopg, "connect", unavailable)

    with pytest.raises(ConfigInvalid) as raised:
        _reset_demo_database(Config(path=None), 42, migration_dsn)

    assert str(raised.value) == (
        "demo database setup failed using IRREVON_MIGRATION_DSN; verify that "
        "Postgres is reachable and the delegated role can create databases"
    )
    assert marker not in str(raised.value)


@pytest.mark.parametrize("seed", [-1, 2_147_483_648])
def test_demo_refuses_seed_outside_owned_database_name_range(seed: int) -> None:
    with pytest.raises(ConfigInvalid, match="demo seed"):
        run_demo(
            Config(path=None),
            seed=seed,
            leg="irrevon",
            keep=False,
            jsonl=True,
            artifact=None,
        )
