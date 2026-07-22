"""Arm R through the real engine (integration: needs the compose Postgres).

Covers the R-specific episode paths — recovery-on-crash, gate denies for
stale authority and cancelled branches, C1 replay, C3 escalation — plus the
DIFFERENTIAL contrast locks against B5 (the flagship premise, §8.6)."""

from __future__ import annotations

import json
import os
from pathlib import Path

import pytest

from irrevon.bench.fixtures import write_dev_split
from irrevon.bench.formats import load_fixture_set
from irrevon.bench.runner import run_unit

pytestmark = pytest.mark.integration

ADMIN_DSN = os.environ.get(
    "IRREVON_TEST_ADMIN_DSN", "postgresql://postgres@127.0.0.1:54329/postgres"
)


@pytest.fixture(scope="module")
def dev_split(tmp_path_factory: pytest.TempPathFactory) -> Path:
    root = tmp_path_factory.mktemp("fixtures")
    write_dev_split(root)
    return root


def _run_r(dev_split: Path, out: Path, workload: str) -> dict:
    outcome = run_unit(
        load_fixture_set(dev_split), workload, "R", out, admin_dsn=ADMIN_DSN
    )
    assert outcome.status == "completed"
    result = json.loads((outcome.run_dir / "result.json").read_text(encoding="utf-8"))
    assert result["validity"]["status"] == "VALID"
    return result


@pytest.mark.parametrize(
    "workload",
    [
        "wl_dev.c2.responselost.irre.r0",
        "wl_dev.c2.semanticresynthesis.irre.r0",
        "wl_dev.c2.retrystorm.irre.r0",
        "wl_dev.c2.crashaftereffectbeforeresponse.irre.r0",
    ],
)
def test_r_zero_duplicates_on_discriminating_faults(
    dev_split: Path, tmp_path: Path, workload: str
) -> None:
    result = _run_r(dev_split, tmp_path, workload)
    assert result["metrics"]["duplicate_effect_rate"]["numerator"] == 0
    assert result["metrics"]["lost_legitimate_effect_rate"]["numerator"] == 0
    assert result["metrics"]["false_suppression_rate"]["numerator"] == 0


def test_r_vs_b5_contrast_on_crash_after_effect(dev_split: Path, tmp_path: Path) -> None:
    """The differential lock: identical fixture + schedule; B5 duplicates, R
    does not. Pinned in BOTH directions — if B5 stops duplicating, the premise
    surfaces as a failure (never weakened, master doc §8.3/§8.6)."""
    workload = "wl_dev.c2.crashaftereffectbeforeresponse.irre.r0"
    r_result = _run_r(dev_split, tmp_path, workload)
    b5_outcome = run_unit(load_fixture_set(dev_split), workload, "B5", tmp_path)
    b5_result = json.loads(
        (b5_outcome.run_dir / "result.json").read_text(encoding="utf-8")
    )
    assert r_result["metrics"]["duplicate_effect_rate"]["numerator"] == 0
    assert b5_result["metrics"]["duplicate_effect_rate"]["numerator"] >= 1


def test_r_suppresses_stale_authority_via_the_real_gate(
    dev_split: Path, tmp_path: Path
) -> None:
    result = _run_r(dev_split, tmp_path, "wl_dev.c2.staleauthorization.irre.r0")
    suppressed = [t for t in result["trials"] if t["arm_outcome"] == "suppressed"]
    assert len(suppressed) == 2  # exactly the two faulted trials
    for trial in suppressed:
        assert trial["detail"]["deny_check"] == "authority"
    # Correct suppression of an expired authority is NOT false suppression:
    # the fixture marks those trials non-legitimate.
    assert result["metrics"]["false_suppression_rate"]["numerator"] == 0


def test_r_suppresses_cancelled_branch_via_the_real_gate(
    dev_split: Path, tmp_path: Path
) -> None:
    result = _run_r(dev_split, tmp_path, "wl_dev.c2.branchcancellation.irre.r0")
    suppressed = [t for t in result["trials"] if t["arm_outcome"] == "suppressed"]
    assert len(suppressed) == 2
    for trial in suppressed:
        assert trial["detail"]["deny_check"] == "branch_lineage"


def test_r_c1_replay_settles_without_duplicates(dev_split: Path, tmp_path: Path) -> None:
    result = _run_r(dev_split, tmp_path, "wl_dev.c1.responselost.irre.r0")
    assert result["metrics"]["duplicate_effect_rate"]["numerator"] == 0
    assert result["metrics"]["duplicate_effect_rate"]["mark"] == "expected-null"


def test_r_c3_escalates_never_auto_settles(dev_split: Path, tmp_path: Path) -> None:
    """The impossibility boundary, demonstrated: on C3 the engine parks and
    escalates — it never invents an outcome (RFC-002 §6.1)."""
    result = _run_r(dev_split, tmp_path, "wl_dev.c3.responselost.irre.r0")
    escalated = [t for t in result["trials"] if t["arm_outcome"] == "escalated"]
    assert len(escalated) == 2
    assert result["metrics"]["human_review_rate"]["numerator"] == 2
    assert result["metrics"]["lost_legitimate_effect_rate"]["mark"] == "fixture-truth-only"
