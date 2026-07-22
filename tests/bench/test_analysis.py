"""Verdict machinery + comparison output against SYNTHETIC fixtures with known
answers (§0 checklist: "analysis code for §5 written against synthetic data").

Nothing here is an observation: every rate is constructed. Margins and gates
are arbitrary test parameters, not proposals for the §0.1 freeze values.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any

from irrevon.bench.analysis import (
    PRIMARY_METRICS,
    RunRecord,
    build_comparison,
    confirmatory_machinery,
)
from irrevon.bench.metrics import METRIC_NAMES

CELLS = ["cellA", "cellB", "cellC", "cellD"]
SEEDS = list(range(10))


def _cell(value: float | None, den: int = 100) -> dict[str, Any]:
    if value is None:
        return {"numerator": None, "denominator": None, "value": None, "mark": "N/A"}
    num = round(value * den)
    return {"numerator": num, "denominator": den, "value": num / den, "mark": None}


def _record(
    arm: str,
    cell: str,
    rep: int,
    rates: dict[str, float | None],
    *,
    valid: bool = True,
    env: str = "sha256:" + "e" * 64,
) -> RunRecord:
    metrics = {name: _cell(rates.get(name)) for name in METRIC_NAMES}
    manifest = {
        "arm": {"arm_id": arm},
        "plan": {"cell_id": cell, "replicate_index": rep, "seed": "1"},
        "environment_digest": env,
        "replaces_run_id": None,
    }
    result = {
        "run_id": f"run_{cell}.{arm}.{rep}".lower().replace("+", "-"),
        "validity": {
            "status": "VALID" if valid else "INVALID",
            "invalid_class": None if valid else "seed-mismatch",
            "evidence": [],
        },
        "metrics": metrics,
        "labels": ["non-confirmatory"],
    }
    return RunRecord(Path(f"/synthetic/{result['run_id']}"), manifest, result)


def _dataset(rate_fn: Any) -> list[RunRecord]:
    """rate_fn(arm, cell, rep) → duplicate rate; orphan/lost fixed at 0.02."""
    records = []
    for arm in ("R", "B5", "B5+B3+B6"):
        for cell in CELLS:
            for rep in SEEDS:
                records.append(
                    _record(
                        arm,
                        cell,
                        rep,
                        {
                            "duplicate_effect_rate": rate_fn(arm, cell, rep),
                            "orphaned_effect_rate": 0.02,
                            "lost_legitimate_effect_rate": 0.02,
                            "false_suppression_rate": 0.0,
                            "unresolved_ambiguous_rate": 0.0,
                            "false_reconciliation_rate": None,
                            "human_review_rate": 0.0,
                            "compensation_correctness": None,
                        },
                    )
                )
    return records


def _machinery(records: list[RunRecord], *, margin: float, gate: float) -> dict[str, Any]:
    return confirmatory_machinery(
        records,
        cells=CELLS,
        reference_arm="R",
        composite_arm="B5+B3+B6",
        b5_arm="B5",
        margin=margin,
        worst_cell_gate_pp=gate,
    )


def test_superiority_fires_when_r_is_clearly_better() -> None:
    def rates(arm: str, cell: str, rep: int) -> float:
        noise = 0.01 * ((rep * 7 + hash(cell) % 5) % 3)  # deterministic jitter
        return (0.02 if arm == "R" else 0.20) + noise

    verdict = _machinery(_dataset(rates), margin=0.01, gate=0.10)
    dup = verdict["per_metric"]["duplicate_effect_rate"]
    assert dup["verdict"] == "superiority"
    assert dup["holm_rejected"] is True
    assert verdict["kill_rule"] == "kill-does-not-fire"
    # The equal metrics are honest limbo, never survival (§5.8).
    assert verdict["per_metric"]["orphaned_effect_rate"]["verdict"] in (
        "inconclusive",
        "equivalence-kill",
    )


def test_kill_fires_on_uniform_equivalence() -> None:
    def rates(arm: str, cell: str, rep: int) -> float:
        return 0.05  # every arm identical everywhere

    verdict = _machinery(_dataset(rates), margin=0.01, gate=0.10)
    assert verdict["kill_rule"] == "kill-fires"
    for metric in PRIMARY_METRICS:
        assert verdict["per_metric"][metric]["verdict"] == "equivalence-kill"
        assert verdict["per_metric"][metric]["tost"]["equivalent"] is True


def test_kill_fires_when_composite_is_better() -> None:
    """Kill clause (b): a baseline that BEATS R kills at least as surely as
    one that ties it (preregistration §1)."""

    def rates(arm: str, cell: str, rep: int) -> float:
        noise = 0.005 * (rep % 3)
        return (0.25 if arm == "R" else 0.05) + noise

    verdict = _machinery(_dataset(rates), margin=0.01, gate=0.30)
    dup = verdict["per_metric"]["duplicate_effect_rate"]
    assert dup["composite_significantly_better"] is True
    assert dup["kill_component_holds"] is True
    assert verdict["kill_rule"] == "kill-fires"


def test_localized_regression_blocks_the_kill() -> None:
    """Worst-cell gate (§5.3 c): pooled equivalence + one cell where the
    composite is worse by ≥ the gate ⇒ 'inconclusive with a localized
    signal' — never a kill, never a win."""

    def rates(arm: str, cell: str, rep: int) -> float:
        if cell == "cellA":
            return 0.05 if arm == "R" else 0.30  # composite much worse here
        if cell == "cellB":
            return 0.30 if arm == "R" else 0.05  # mirrored so the pool ties
        return 0.10

    verdict = _machinery(_dataset(rates), margin=0.01, gate=0.10)
    dup = verdict["per_metric"]["duplicate_effect_rate"]
    assert dup["tost"]["equivalent"] is True
    assert dup["worst_cell"]["fired"] is True
    assert verdict["kill_rule"] == "inconclusive-with-localized-signal"
    assert dup["verdict"] == "inconclusive-with-localized-signal"


def test_verdict_always_labeled_non_confirmatory_pre_freeze() -> None:
    verdict = _machinery(_dataset(lambda a, c, r: 0.05), margin=0.01, gate=0.10)
    assert verdict["confirmatory"] is False
    assert "non-confirmatory" in verdict["labels"]
    assert verdict["parameters"]["margin"] == 0.01  # echoed, never defaulted


def test_insufficient_seeds_reported_not_guessed() -> None:
    records = [
        _record("R", "cellA", 0, dict.fromkeys(PRIMARY_METRICS, 0.05)),
        _record("B5", "cellA", 0, dict.fromkeys(PRIMARY_METRICS, 0.05)),
        _record("B5+B3+B6", "cellA", 0, dict.fromkeys(PRIMARY_METRICS, 0.05)),
    ]
    verdict = confirmatory_machinery(
        records, cells=["cellA"], reference_arm="R", composite_arm="B5+B3+B6",
        b5_arm="B5", margin=0.01, worst_cell_gate_pp=0.10,
    )
    for metric in PRIMARY_METRICS:
        assert verdict["per_metric"][metric]["verdict"] == "insufficient-seeds"
    assert verdict["kill_rule"] == "kill-does-not-fire"


def test_invalid_runs_counted_and_excluded_from_rates() -> None:
    records = _dataset(lambda a, c, r: 0.05)
    records.append(
        _record("R", "cellA", 99, {"duplicate_effect_rate": 0.99}, valid=False)
    )
    comparison = build_comparison(records)
    assert comparison["run_accounting"]["invalid"] == 1
    assert comparison["run_accounting"]["invalid_run_ids"] == ["run_cella.r.99"]
    # The INVALID run's 0.99 must not have entered any pooled rate.
    pooled = comparison["table"]["R"]["cellA"]["metrics"]["duplicate_effect_rate"]
    assert pooled["pooled_rate"] < 0.99


def test_environment_drift_is_reported() -> None:
    records = _dataset(lambda a, c, r: 0.05)
    records.append(
        _record(
            "R", "cellA", 98, {"duplicate_effect_rate": 0.05},
            env="sha256:" + "f" * 64,
        )
    )
    comparison = build_comparison(records)
    assert comparison["environment_drift"]["drifted"] is True
    assert comparison["environment_drift"]["distinct_environments"] == 2
