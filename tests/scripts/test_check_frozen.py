"""Scenario tests for scripts/check-frozen.sh — the frozen/append-only diff gate.

Each scenario builds a scratch git repo, applies a mutation on a work branch, and
runs the gate in range mode (BASE_REF=main) — the exact mode CI uses on PRs.
The negative scenarios pin the gate's fail-closed behavior: a frozen/append-only
file changed WITHOUT the paired human-ratification evidence must keep failing.
"""

from __future__ import annotations

import os
import shutil
import subprocess
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).parent.parent.parent
GATE = REPO_ROOT / "scripts" / "check-frozen.sh"

BASE_QUEUE = (
    "# Review queue\n\n"
    "| AM-1 | some change | PROPOSED |\n"
    "| AM-2 | other change | PROPOSED |\n"
)


def _git(repo: Path, *args: str) -> None:
    subprocess.run(
        ["git", "-c", "user.name=test", "-c", "user.email=test@detent.invalid", *args],
        cwd=repo,
        check=True,
        capture_output=True,
    )


def _commit_all(repo: Path) -> None:
    _git(repo, "add", "-A")
    _git(repo, "commit", "-q", "-m", "change under test")


def _run_gate(repo: Path) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        ["bash", "scripts/check-frozen.sh"],
        cwd=repo,
        env={**os.environ, "BASE_REF": "main"},
        capture_output=True,
        text=True,
    )


@pytest.fixture
def scratch_repo(tmp_path: Path) -> Path:
    repo = tmp_path / "repo"
    (repo / "docs").mkdir(parents=True)
    (repo / "scripts").mkdir()
    (repo / "docs" / "master-doc.md").write_text("# Master doc\n\nfrozen body\n")
    (repo / "scripts" / "master-doc.sha256").write_text("0" * 64 + "\n")
    (repo / "docs" / "review-queue.md").write_text(BASE_QUEUE)
    shutil.copy(GATE, repo / "scripts" / "check-frozen.sh")
    _git(repo, "init", "-q", "-b", "main")
    _commit_all(repo)
    _git(repo, "checkout", "-q", "-b", "work")
    return repo


# ── negative scenarios: missing evidence must keep failing ────────────────────


def test_master_doc_change_without_pin_fails(scratch_repo: Path) -> None:
    (scratch_repo / "docs" / "master-doc.md").write_text("# Master doc\n\nedited body\n")
    _commit_all(scratch_repo)
    result = _run_gate(scratch_repo)
    assert result.returncode == 1
    assert "without scripts/master-doc.sha256" in result.stdout


def test_review_queue_deletion_without_repin_fails(scratch_repo: Path) -> None:
    # Even WITH a recorded RATIFIED line, deletions without the master-doc
    # re-pin in the same range must fail: the re-pin is the human-only act.
    (scratch_repo / "docs" / "review-queue.md").write_text(
        "# Review queue\n\n| AM-2 | other change | RATIFIED 2026-07-21 |\n"
    )
    _commit_all(scratch_repo)
    result = _run_gate(scratch_repo)
    assert result.returncode == 1
    assert "append-only" in result.stdout


def test_review_queue_deletion_with_repin_but_no_ratified_line_fails(
    scratch_repo: Path,
) -> None:
    (scratch_repo / "docs" / "master-doc.md").write_text("# Master doc\n\namended body\n")
    (scratch_repo / "scripts" / "master-doc.sha256").write_text("1" * 64 + "\n")
    (scratch_repo / "docs" / "review-queue.md").write_text(
        "# Review queue\n\n| AM-2 | other change | PROPOSED |\n"
    )
    _commit_all(scratch_repo)
    result = _run_gate(scratch_repo)
    assert result.returncode == 1
    assert "append-only" in result.stdout


# ── positive scenarios ─────────────────────────────────────────────────────────


def test_ratification_integration_passes(scratch_repo: Path) -> None:
    # The sanctioned exception: re-pin + queue restructure recording RATIFIED AM-<n>.
    (scratch_repo / "docs" / "master-doc.md").write_text("# Master doc\n\namended body\n")
    (scratch_repo / "scripts" / "master-doc.sha256").write_text("1" * 64 + "\n")
    (scratch_repo / "docs" / "review-queue.md").write_text(
        "# Review queue\n\n"
        "| AM-1 | some change | RATIFIED 2026-07-21 |\n"
        "| AM-2 | other change | RATIFIED 2026-07-21 |\n"
    )
    _commit_all(scratch_repo)
    result = _run_gate(scratch_repo)
    assert result.returncode == 0, result.stdout
    assert "ratification integration" in result.stdout


def test_pure_append_to_review_queue_passes(scratch_repo: Path) -> None:
    (scratch_repo / "docs" / "review-queue.md").write_text(
        BASE_QUEUE + "| AM-3 | appended item | PROPOSED |\n"
    )
    _commit_all(scratch_repo)
    result = _run_gate(scratch_repo)
    assert result.returncode == 0, result.stdout
    assert "review-queue append-only OK" in result.stdout
