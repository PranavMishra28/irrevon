"""First-slice CLI surface (RFC-002 §12): init · doctor · demo · inspect."""

from __future__ import annotations

import json
import subprocess
import sys
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

import psycopg
import pytest
from psycopg.rows import dict_row

from irrevon.cli import main
from tests.integration.conftest import ADMIN_DSN, DBHandles

pytestmark = pytest.mark.integration

REPO_ROOT = Path(__file__).parent.parent.parent


# ── irrevon init ───────────────────────────────────────────────────────────────


def test_init_writes_templates_non_destructively(tmp_path: Path, capsys: Any) -> None:
    # Pin the config to an unreachable DSN so init's migration attempt cannot
    # touch any real database from the test environment.
    unreachable = tmp_path / "cfg" / "irrevon.toml"
    unreachable.parent.mkdir()
    unreachable.write_text(
        'schema_version = "1"\n\n[ledger]\ndsn = "postgresql://nobody@127.0.0.1:1/none"\n'
    )
    rc = main(["init", "--dir", str(tmp_path), "--json", "--config", str(unreachable)])
    assert rc == 0
    out = json.loads(capsys.readouterr().out)
    assert sorted(out["written"]) == [".env.example", "compose.yaml", "irrevon.toml"]
    assert out["next"] == "irrevon doctor"
    assert out["migrations_applied"] is None and out["db_note"], (
        "unreachable DB is a normal first-run state, reported not fatal"
    )
    # Placeholders only — never a credential value.
    env_example = (tmp_path / ".env.example").read_text()
    assert "change-me-locally" in env_example
    compose = (tmp_path / "compose.yaml").read_text()
    assert "sha256:" in compose, "compose Postgres is digest-pinned"
    assert "127.0.0.1:5432" in compose, "loopback only"

    # Refuses to overwrite without --force.
    (tmp_path / "irrevon.toml").write_text("# user-edited\nschema_version = \"1\"\n")
    rc = main(["init", "--dir", str(tmp_path), "--json", "--config", str(unreachable)])
    out = json.loads(capsys.readouterr().out)
    assert rc == 0
    assert "irrevon.toml" in out["skipped"]
    assert (tmp_path / "irrevon.toml").read_text().startswith("# user-edited")

    rc = main(
        ["init", "--dir", str(tmp_path), "--force", "--json", "--config",
         str(unreachable)]
    )
    out = json.loads(capsys.readouterr().out)
    assert "irrevon.toml" in out["written"]


# ── irrevon doctor ─────────────────────────────────────────────────────────────


def _write_config(tmp_path: Path, dsn: str) -> Path:
    cfg = tmp_path / "irrevon.toml"
    cfg.write_text(
        f'schema_version = "1"\n\n[ledger]\ndsn = "{dsn}"\n\n[demo]\nseed = 4242\n'
    )
    return cfg


def test_doctor_is_read_only_and_green(
    fresh_db: DBHandles, tmp_path: Path, capsys: Any
) -> None:
    cfg = _write_config(tmp_path, fresh_db.admin_dsn)

    def counts() -> dict[str, int]:
        with psycopg.connect(fresh_db.admin_dsn, row_factory=dict_row) as conn:
            return {
                t: conn.execute(f"SELECT count(*) AS n FROM {t}").fetchone()["n"]  # type: ignore[index,union-attr]
                for t in ("effect_records", "effect_transitions", "gate_decisions",
                          "findings")
            }

    before = counts()
    rc = main(["doctor", "--json", "--config", str(cfg)])
    out = json.loads(capsys.readouterr().out)
    assert rc == 0, f"doctor failed: {out}"
    assert out["ok"] is True
    by_name = {c["name"]: c for c in out["checks"]}
    # T-104 acceptance: the identity self-test reproduces the pinned vectors.
    assert by_name["identity_selftest"]["status"] == "ok"
    assert by_name["ledger_db"]["status"] == "ok"
    assert by_name["ledger_write"]["status"] == "ok"
    assert counts() == before, "doctor must never mutate (RFC-002 §12)"


def test_doctor_fails_cleanly_when_db_unreachable(
    tmp_path: Path, capsys: Any
) -> None:
    cfg = _write_config(tmp_path, "postgresql://postgres@127.0.0.1:1/nope")
    rc = main(["doctor", "--json", "--config", str(cfg)])
    out = json.loads(capsys.readouterr().out)
    assert rc == 3  # declared outcome, not a crash
    assert out["ok"] is False


def test_config_unknown_keys_rejected(tmp_path: Path, capsys: Any) -> None:
    cfg = tmp_path / "irrevon.toml"
    cfg.write_text('schema_version = "1"\n\n[ledgr]\ndsn = "x"\n')
    rc = main(["doctor", "--config", str(cfg)])
    captured = capsys.readouterr()
    assert rc == 1
    envelope = json.loads(captured.err.strip().splitlines()[-1])
    assert envelope["error"]["code"] == "config_invalid"


# ── irrevon demo (the acceptance criterion) ────────────────────────────────────


def test_demo_exits_zero_with_the_contrast(
    template_db: str, tmp_path: Path
) -> None:
    """T-104 acceptance: `irrevon demo` exits 0 with the Irrevon leg at 1
    destination effect + reconciled SETTLED_COMMITTED + evidenced dedup deny,
    and the B5 leg at 2 destination effects, proven by read-back."""
    _write_config(tmp_path, ADMIN_DSN)
    proc = subprocess.run(
        [sys.executable, "-m", "irrevon.cli", "demo", "--jsonl", "--no-keep",
         "--seed", "4242", "--config", str(tmp_path / "irrevon.toml")],
        capture_output=True,
        text=True,
        cwd=REPO_ROOT,
        timeout=180,
    )
    assert proc.returncode == 0, f"demo failed:\n{proc.stdout}\n{proc.stderr}"
    lines = [json.loads(line) for line in proc.stdout.strip().splitlines()]
    summary = lines[-1]
    assert summary["contrast_holds"] is True
    assert summary["irrevon_leg"]["destination_effects"] == 1
    assert summary["irrevon_leg"]["duplicate_rejected"] is True
    assert summary["irrevon_leg"]["reconciled"] == "SETTLED_COMMITTED"
    assert summary["b5_leg"]["destination_effects"] == 2
    assert summary["b5_leg"]["duplicate_created"] is True
    events = [line.get("event") for line in lines[:-1]]
    for expected in (
        "registered",
        "dispatch_response_lost",
        "crash",
        "recovered",
        "settled_confirmed_unique",
        "resynthesis_collapsed",
        "duplicate_rejected",
        "b5_response_lost",
        "b5_retried",
        "b5_duplicate",
    ):
        assert expected in events, f"missing demo event {expected}"


# ── irrevon inspect ────────────────────────────────────────────────────────────


@pytest.fixture
def settled_effect(fresh_db: DBHandles) -> tuple[str, str]:
    from irrevon.adapters.base import declarations_dir, load_declaration
    from irrevon.adapters.refdest import RefDest, RefdestAdapter
    from irrevon.api import Engine

    declaration = load_declaration(declarations_dir() / "refdest-c2.capability.json")
    refdest = RefDest(seed=5)
    adapter = RefdestAdapter("refdest-c2", declaration, instance=refdest)
    with Engine(fresh_db.app_dsn, {"refdest-c2": adapter}) as engine:
        engine.boot()
        reg = engine.register_intent(
            {
                "schema_version": "1",
                "stable_ids": {"order_id": "insp-9410"},
                "effect_type": "order.create",
                "effect_class": "IRREVERSIBLE",
                "scope": "inspect/prod",
                "adapter_id": "refdest-c2",
                "parameters": {"secret_looking_value": "not-an-identity-input"},
                "authority_ref": "auth_insp",
                "stamped_at": datetime.now(UTC).isoformat().replace("+00:00", "Z"),
            }
        )
        refdest.control_schedule(
            [{"match": {"op": "create"}, "fault": "DROP_RESPONSE_AFTER_COMMIT"}]
        )
        engine.dispatch(reg.effect_id)
        engine.reconcile(reg.effect_id)
        # The re-synthesized deny, so inspect shows deny evidence too.
        engine.dispatch(reg.effect_id)
    return fresh_db.admin_dsn, reg.effect_id


def test_inspect_shows_evidence_and_integrity(
    settled_effect: tuple[str, str], capsys: Any
) -> None:
    dsn, effect_id = settled_effect
    rc = main(["inspect", effect_id, "--dsn", dsn])
    out = capsys.readouterr().out
    assert rc == 0
    # Redacted by default: stable-id VALUES never shown without --reveal.
    assert "insp-9410" not in out
    assert "<redacted" in out
    assert "SETTLED_COMMITTED" in out
    assert "CONFIRMED_UNIQUE" in out
    assert "check=dedup" in out
    assert "matches effect_id: YES" in out

    rc = main(["inspect", effect_id, "--dsn", dsn, "--reveal"])
    out = capsys.readouterr().out
    assert "insp-9410" in out


def test_inspect_json_view(settled_effect: tuple[str, str], capsys: Any) -> None:
    dsn, effect_id = settled_effect
    rc = main(["inspect", effect_id, "--dsn", dsn, "--json"])
    assert rc == 0
    view = json.loads(capsys.readouterr().out)
    assert view["classification"] == "CONFIRMED_UNIQUE"
    assert view["integrity"]["matches"] is True
    assert view["integrity"]["recomputed_intent_id"] == effect_id
    assert view["record"]["lifecycle"] == "SETTLED_COMMITTED"
    assert [d["outcome"] for d in view["gate_decisions"]] == ["ALLOW", "DENY"]


def test_inspect_unknown_id_is_exit_3(fresh_db: DBHandles, capsys: Any) -> None:
    rc = main(["inspect", "f" * 64, "--dsn", fresh_db.admin_dsn])
    assert rc == 3
