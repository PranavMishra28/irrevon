"""The public CLI help is complete, descriptive, and generated from one parser."""

from __future__ import annotations

import subprocess
import sys

import pytest

COMMANDS = [
    (),
    ("init",),
    ("doctor",),
    ("demo",),
    ("serve",),
    ("worker",),
    ("inspect",),
    ("bench",),
    ("bench", "fixtures"),
    ("bench", "validate"),
    ("bench", "smoke"),
    ("bench", "conform"),
    ("bench", "analyze"),
    ("bench", "run"),
    ("bench", "freeze"),
]


@pytest.mark.parametrize("command", COMMANDS, ids=lambda command: " ".join(command) or "root")
def test_every_public_command_has_help(command: tuple[str, ...]) -> None:
    proc = subprocess.run(
        [sys.executable, "-m", "irrevon.cli", *command, "--help"],
        check=False,
        capture_output=True,
        text=True,
        timeout=30,
    )

    assert proc.returncode == 0, proc.stderr
    assert proc.stderr == ""
    assert "usage: irrevon" in proc.stdout
    assert "options:" in proc.stdout


def test_help_does_not_offer_inert_common_flags() -> None:
    init = subprocess.run(
        [sys.executable, "-m", "irrevon.cli", "init", "--help"],
        check=True,
        capture_output=True,
        text=True,
        timeout=30,
    ).stdout
    serve = subprocess.run(
        [sys.executable, "-m", "irrevon.cli", "serve", "--help"],
        check=True,
        capture_output=True,
        text=True,
        timeout=30,
    ).stdout

    assert "--no-color" not in init
    assert "--quiet" not in init
    assert "--quiet" in serve
    assert "suppress HTTP request logs" in serve


def test_first_use_flags_explain_effects_and_defaults() -> None:
    init = subprocess.run(
        [sys.executable, "-m", "irrevon.cli", "init", "--help"],
        check=True,
        capture_output=True,
        text=True,
        timeout=30,
    ).stdout
    demo = subprocess.run(
        [sys.executable, "-m", "irrevon.cli", "demo", "--help"],
        check=True,
        capture_output=True,
        text=True,
        timeout=30,
    ).stdout
    inspect = subprocess.run(
        [sys.executable, "-m", "irrevon.cli", "inspect", "--help"],
        check=True,
        capture_output=True,
        text=True,
        timeout=30,
    ).stdout

    assert "overwrite scaffold files" in init
    assert "directory to scaffold (default: current directory)" in init
    assert "IRREVON_MIGRATION_DSN" in init
    assert "deterministic demo seed" in demo
    assert "conventional durable retry" in demo
    assert "effect id or stable upstream identifier" in inspect
