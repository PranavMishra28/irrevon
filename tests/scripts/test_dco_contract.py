"""Behavioral contract for mandatory, non-spoofable DCO sign-off."""

from __future__ import annotations

import os
import subprocess
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
CHECK = ROOT / "scripts" / "check-dco.sh"


def _git(
    repo: Path, *args: str, env: dict[str, str] | None = None
) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        ["git", *args],
        cwd=repo,
        env=env,
        check=True,
        text=True,
        capture_output=True,
    )


def test_dependabot_author_string_does_not_bypass_signoff(tmp_path: Path) -> None:
    repo = tmp_path / "repo"
    repo.mkdir()
    _git(repo, "init", "--initial-branch=main")
    _git(repo, "config", "user.name", "Test Committer")
    _git(repo, "config", "user.email", "committer@example.invalid")

    tracked = repo / "tracked.txt"
    tracked.write_text("base\n")
    _git(repo, "add", "tracked.txt")
    _git(repo, "commit", "--no-gpg-sign", "-m", "base")
    base = _git(repo, "rev-parse", "HEAD").stdout.strip()

    tracked.write_text("spoofed\n")
    spoofed_env = os.environ.copy()
    spoofed_env.update(
        {
            "GIT_AUTHOR_NAME": "dependabot[bot]",
            "GIT_AUTHOR_EMAIL": "49699333+dependabot[bot]@users.noreply.github.com",
        }
    )
    _git(repo, "commit", "--no-gpg-sign", "-am", "unsigned spoof", env=spoofed_env)

    result = subprocess.run(
        ["bash", str(CHECK), base, "HEAD"],
        cwd=repo,
        check=False,
        text=True,
        capture_output=True,
    )
    assert result.returncode == 1
    assert "lacks a syntactically valid Signed-off-by trailer" in result.stderr
