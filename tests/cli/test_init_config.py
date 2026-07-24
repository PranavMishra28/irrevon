"""Focused unit contracts for init failure handling and DSN resolution."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import psycopg
import pytest
from psycopg.conninfo import conninfo_to_dict

from irrevon.cli import main
from irrevon.cli.config import DEFAULT_DSN, Config
from irrevon.errors import ConfigInvalid, StorageUnavailable
from irrevon.ledger import db as ledger_db

_PASSWORD_ENV = "IRREVON_TEST_LEDGER_PASSWORD"
_SYNTHETIC_PASSWORD = (
    "not-a-real-secret ' \" \\\n application_name=must-not-inject @:/?#&=%+"
)


def _write_config(tmp_path: Path) -> Path:
    config = tmp_path / "source-config.toml"
    config.write_text(
        'schema_version = "1"\n\n'
        "[ledger]\n"
        'dsn = "postgresql://irrevon@localhost:5432/irrevon"\n'
        f'password_env = "{_PASSWORD_ENV}"\n',
        encoding="utf-8",
    )
    return config


def test_resolved_dsn_round_trips_opaque_password_without_parameter_injection(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv(_PASSWORD_ENV, _SYNTHETIC_PASSWORD)
    resolved = Config(
        path=None,
        dsn="postgresql://irrevon@localhost:5432/irrevon",
        password_env=_PASSWORD_ENV,
    ).resolved_dsn()

    parsed = conninfo_to_dict(resolved)
    assert parsed["password"] == _SYNTHETIC_PASSWORD
    assert parsed["user"] == "irrevon"
    assert parsed["host"] == "localhost"
    assert parsed["port"] == "5432"
    assert parsed["dbname"] == "irrevon"
    assert "application_name" not in parsed


def test_resolved_dsn_rejects_invalid_input_without_environment_value_leak(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv(_PASSWORD_ENV, _SYNTHETIC_PASSWORD)
    config = Config(
        path=None,
        dsn="not valid PostgreSQL connection information",
        password_env=_PASSWORD_ENV,
    )

    with pytest.raises(ConfigInvalid) as raised:
        config.resolved_dsn()

    assert str(raised.value) == (
        "ledger.dsn is not valid PostgreSQL connection information"
    )
    assert _SYNTHETIC_PASSWORD not in str(raised.value)


def test_default_dsn_uses_the_scaffolded_runtime_role() -> None:
    assert conninfo_to_dict(DEFAULT_DSN)["user"] == "irrevon_app"


@pytest.mark.parametrize(
    "body",
    [
        'schema_version = "1"\nledger = 7\n',
        'schema_version = "1"\ndemo = 7\n',
        'schema_version = "1"\n[ledger]\ndsn = 7\n',
        'schema_version = "1"\n[ledger]\npassword_env = 7\n',
        'schema_version = "1"\n[ledger]\npassword_env = "BAD=NAME"\n',
        'schema_version = "1"\n[demo]\nseed = "42"\n',
        'schema_version = "1"\n[demo]\nseed = 4.9\n',
        'schema_version = "1"\n[demo]\nseed = true\n',
        ('schema_version = "1"\n[adapters.synthetic]\nkind = 7\n'),
        (
            'schema_version = "1"\n'
            '[adapters.synthetic]\nkind = "refdest"\ncredentials = "BAD=NAME"\n'
        ),
    ],
)
def test_malformed_config_types_return_stable_cli_envelope(
    tmp_path: Path,
    capsys: pytest.CaptureFixture[str],
    body: str,
) -> None:
    path = tmp_path / "invalid.toml"
    path.write_text(body, encoding="utf-8")
    rc = main(["doctor", "--config", str(path), "--json"])
    captured = capsys.readouterr()
    assert rc == 1
    assert captured.out == ""
    envelope = json.loads(captured.err)
    assert envelope["error"]["code"] == "config_invalid"
    assert "Traceback" not in captured.err


def test_init_treats_only_storage_unavailable_as_nonfatal(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    config = _write_config(tmp_path)
    monkeypatch.setenv(_PASSWORD_ENV, _SYNTHETIC_PASSWORD)
    monkeypatch.setenv(
        "IRREVON_MIGRATION_DSN",
        Config(
            path=config,
            dsn="postgresql://irrevon@localhost:5432/irrevon",
            password_env=_PASSWORD_ENV,
        ).resolved_dsn(),
    )

    def unavailable(dsn: str) -> list[str]:
        assert conninfo_to_dict(dsn)["password"] == _SYNTHETIC_PASSWORD
        raise StorageUnavailable(f"synthetic unreachable detail {_SYNTHETIC_PASSWORD}")

    monkeypatch.setattr(ledger_db, "apply_migrations", unavailable)
    rc = main(
        [
            "init",
            "--dir",
            str(tmp_path / "output"),
            "--config",
            str(config),
            "--json",
        ]
    )

    captured = capsys.readouterr()
    payload = json.loads(captured.out)
    assert rc == 0
    assert payload["migrations_applied"] is None
    assert payload["db_note"] == (
        "ledger DB not reachable yet — start it (docker compose up -d --wait) "
        "and re-run `irrevon init` to apply migrations"
    )
    assert captured.err == ""
    assert _SYNTHETIC_PASSWORD not in captured.out


@pytest.mark.parametrize("as_json", [False, True], ids=["plain", "json"])
@pytest.mark.parametrize(
    "failure",
    [
        RuntimeError("migration integrity mismatch"),
        psycopg.ProgrammingError("synthetic SQL failure"),
        AssertionError("synthetic programming failure"),
    ],
    ids=["integrity", "sql", "programming"],
)
def test_init_migration_failures_are_sanitized_and_fail_closed(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
    as_json: bool,
    failure: Exception,
) -> None:
    config = _write_config(tmp_path)
    monkeypatch.setenv(_PASSWORD_ENV, _SYNTHETIC_PASSWORD)
    monkeypatch.setenv(
        "IRREVON_MIGRATION_DSN",
        Config(
            path=config,
            dsn="postgresql://irrevon@localhost:5432/irrevon",
            password_env=_PASSWORD_ENV,
        ).resolved_dsn(),
    )

    def fail_migration(dsn: str) -> list[str]:
        assert conninfo_to_dict(dsn)["password"] == _SYNTHETIC_PASSWORD
        failure.args = (f"{failure.args[0]}: {_SYNTHETIC_PASSWORD}",)
        raise failure

    monkeypatch.setattr(ledger_db, "apply_migrations", fail_migration)
    argv = [
        "init",
        "--dir",
        str(tmp_path / "output"),
        "--config",
        str(config),
    ]
    if as_json:
        argv.append("--json")

    rc = main(argv)

    captured = capsys.readouterr()
    assert rc == 1
    assert captured.out == ""
    envelope: dict[str, Any] = json.loads(captured.err)
    assert envelope == {
        "schema_version": "1",
        "error": {
            "code": "unexpected",
            "message": "ledger migration failed; initialization did not complete",
            "retryable": False,
            "details": {},
        },
    }
    assert _SYNTHETIC_PASSWORD not in captured.err
    assert type(failure).__name__ not in captured.err
