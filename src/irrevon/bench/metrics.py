"""Metric computation — preregistration §4, oracle-fixed denominators.

Every denominator comes from the FIXTURE (workload labels) or the ORACLE
read-back — never from arm-side counts — so an arm cannot change the
denominator it is judged by, and cross-arm comparison never rewards adopting
any particular internal data model.

Pre-specified non-numeric cells (§2.1/§4) are marked, never zero-filled:
``N/A`` (zero denominator), ``N/A-by-arm`` (the arm lacks the concept),
``expected-null`` (C1 duplicate cells under replay-window faults, L3),
``fixture-truth-only`` (C3 lost/orphan cells, L1). Marks accompany values
where a value exists but is qualified.
"""

from __future__ import annotations

from typing import Any

from irrevon.bench.oracle import OracleReadback

__all__ = ["METRIC_NAMES", "compute_metrics", "metric_cell", "na_cell"]

METRIC_NAMES = (
    "duplicate_effect_rate",
    "orphaned_effect_rate",
    "lost_legitimate_effect_rate",
    "false_suppression_rate",
    "unresolved_ambiguous_rate",
    "false_reconciliation_rate",
    "human_review_rate",
    "compensation_correctness",
)

_EXPECTED_NULL_C1_FAULTS = {
    "retry-storm",
    "response-lost",
    "crash-after-effect-before-response",
}


def metric_cell(numerator: int, denominator: int, mark: str | None = None) -> dict[str, Any]:
    """A rate cell; zero denominators become N/A (pre-specified rule, §4)."""
    if denominator <= 0:
        return na_cell("N/A")
    return {
        "numerator": numerator,
        "denominator": denominator,
        "value": numerator / denominator,
        "mark": mark,
    }


def na_cell(mark: str) -> dict[str, Any]:
    return {"numerator": None, "denominator": None, "value": None, "mark": mark}


def compute_metrics(
    workload: dict[str, Any],
    trial_reports: list[dict[str, Any]],
    readback: OracleReadback,
    *,
    ambiguity_concept: bool,
    classifies: bool,
) -> dict[str, dict[str, Any]]:
    """The §4 metric table for one (cell, replicate, arm) unit."""
    cell = workload["cell"]
    tier: str = cell["tier"]
    fault: str = cell["fault"]

    eligible = [t for t in workload["trials"] if t["eligible_for_dispatch"]]
    legitimate = [
        t for t in workload["trials"] if t["legitimate"] and t["eligible_for_dispatch"]
    ]
    counts = readback.per_intent_effect_counts
    reports_by_trial = {r["trial_index"]: r for r in trial_reports}

    # Duplicate rate: Σ max(0, n − 1) over eligible intents ÷ eligible intents.
    duplicate_num = sum(
        max(0, counts.get(str(t["trial_index"]), 0) - 1) for t in eligible
    )
    duplicate_mark = (
        "expected-null" if tier == "C1" and fault in _EXPECTED_NULL_C1_FAULTS else None
    )
    duplicate = metric_cell(duplicate_num, len(eligible), duplicate_mark)

    # Orphaned rate: unattributable destination effects ÷ total destination effects.
    orphan_mark = "fixture-truth-only" if tier == "C3" else None
    orphaned = metric_cell(readback.orphan_effect_count, readback.total_effects, orphan_mark)

    # Lost-legitimate rate: legitimate intended effects absent at read-back.
    lost_num = sum(
        1 for t in legitimate if counts.get(str(t["trial_index"]), 0) == 0
    )
    lost_mark = "fixture-truth-only" if tier == "C3" else None
    lost = metric_cell(lost_num, len(legitimate), lost_mark)

    # False suppression: legitimate effects the arm blocked AND absent at read-back.
    suppression_num = 0
    for t in legitimate:
        report = reports_by_trial.get(t["trial_index"])
        if report is None:
            continue
        if (
            report["arm_outcome"] == "suppressed"
            and counts.get(str(t["trial_index"]), 0) == 0
        ):
            suppression_num += 1
    false_suppression = metric_cell(suppression_num, len(legitimate))

    dispatched = sum(1 for r in trial_reports if r["dispatch_attempted"])

    # Unresolved-ambiguous: arm-conditional (requires an ambiguity concept).
    if not ambiguity_concept:
        unresolved = na_cell("N/A-by-arm")
    else:
        unresolved_num = sum(
            1 for r in trial_reports if r["arm_outcome"] == "ambiguous-unresolved"
        )
        unresolved = metric_cell(unresolved_num, dispatched)

    # False reconciliation: arm-conditional (requires oracle-visible claims).
    if not classifies:
        false_reconciliation = na_cell("N/A-by-arm")
    else:
        claims = 0
        wrong = 0
        for r in trial_reports:
            claim = r.get("detail", {}).get("oracle_claim")
            if claim is None:
                continue
            claims += 1
            n = counts.get(str(r["trial_index"]), 0)
            if (claim == "unique" and n != 1) or (claim == "absent" and n != 0):
                wrong += 1
        false_reconciliation = metric_cell(wrong, claims)

    # Human review rate: escalations ÷ dispatched trials.
    escalations = sum(1 for r in trial_reports if r["arm_outcome"] == "escalated")
    human_review = metric_cell(escalations, dispatched)

    # Compensation correctness: denominator = compensations ATTEMPTED; arms
    # that never compensate report N/A — never a penalty or a credit (§2.1).
    compensations = [
        r for r in trial_reports if r.get("detail", {}).get("compensation_attempted")
    ]
    if not compensations:
        compensation = na_cell("N/A")
    else:
        correct = sum(
            1 for r in compensations if r["detail"].get("compensation_correct") is True
        )
        compensation = metric_cell(correct, len(compensations))

    return {
        "duplicate_effect_rate": duplicate,
        "orphaned_effect_rate": orphaned,
        "lost_legitimate_effect_rate": lost,
        "false_suppression_rate": false_suppression,
        "unresolved_ambiguous_rate": unresolved,
        "false_reconciliation_rate": false_reconciliation,
        "human_review_rate": human_review,
        "compensation_correctness": compensation,
    }
