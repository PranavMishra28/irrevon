"""Security regressions for demo handoff and destructive-name bounds."""

from __future__ import annotations

import pytest

from irrevon.cli.config import Config
from irrevon.cli.demo import _display_demo_dsn, run_demo
from irrevon.errors import ConfigInvalid


def test_display_demo_dsn_never_contains_password() -> None:
    marker = "opaque-password-that-must-not-print"
    config = Config(
        path=None,
        dsn=f"postgresql://irrevon:{marker}@localhost:5432/irrevon",
    )
    shown = _display_demo_dsn(config, "irrevon_demo_s42")
    assert marker not in shown
    assert "password" not in shown
    assert "dbname=irrevon_demo_s42" in shown


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
