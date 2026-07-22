"""Causal-history compilation + invariant checker: counterexample-driven.

Every invariant is exercised with a constructed history that MUST violate it
(oracle counterexamples), plus clean histories that must not. The cross-check
tests prove the differential guard fires on doctored metrics — the mechanism
that keeps the metric pipeline and the history checker mutually honest."""

from __future__ import annotations

from typing import Any

from irrevon.bench.history import (
    check_history,
    compile_history,
    cross_check_metrics,
)
from irrevon.bench.oracle import AttributedEffect, OracleReadback


def _workload(n: int = 2, **flag_overrides: dict[int, dict[str, Any]]) -> dict[str, Any]:
    trials = []
    for i in range(n):
        trial = {
            "trial_index": i,
            "stable_ids": {"order_id": str(1000 + i)},
            "effect_type": "order.create",
            "scope": "test",
            "parameters": {"order_id": str(1000 + i)},
            "authority_ref": f"auth_{i}",
            "legitimate": True,
            "eligible_for_dispatch": True,
        }
        trial.update(flag_overrides.get("flags", {}).get(i, {}))
        trials.append(trial)
    return {
        "workload_id": "wl_test.hist",
        "cell_id": "C2/refdest/response-lost/IRREVERSIBLE",
        "replicate_index": 0,
        "cell": {"fault": "response-lost", "effect_class": "IRREVERSIBLE",
                 "tier": "C2", "destination_kind": "refdest", "stratum": "S-REF"},
        "trials": trials,
    }


def _schedule(injections: list[dict[str, Any]]) -> dict[str, Any]:
    return {"schedule_id": "fs_test.hist", "workload_id": "wl_test.hist",
            "injections": injections}


def _report(i: int, outcome: str, dispatched: bool = True, **detail: Any) -> dict[str, Any]:
    detail.setdefault("log", [{"action": "dispatch", "transport_outcome": "OK"}])
    return {"trial_index": i, "arm_outcome": outcome,
            "dispatch_attempted": dispatched, "detail": detail}


def _effect(seq: int, intent_key: str | None, *, via: str = "api",
            ambiguous: bool = False) -> AttributedEffect:
    return AttributedEffect(
        destination_ref=f"dest_{seq}", request_seq=seq, created_at=f"T{seq}",
        via=via, intent_key=intent_key,
        attributed_by="digest" if intent_key else None, ambiguous=ambiguous,
    )


def _readback(effects: list[AttributedEffect], n_trials: int = 2) -> OracleReadback:
    per_intent = {str(i): 0 for i in range(n_trials)}
    orphans = 0
    for e in effects:
        if e.intent_key is None:
            orphans += 1
        else:
            per_intent[e.intent_key] = per_intent.get(e.intent_key, 0) + 1
    return OracleReadback(
        total_effects=len(effects), per_intent_effect_counts=per_intent,
        orphan_effect_count=orphans, ambiguous_attributions=0,
        readback_digest="sha256:" + "0" * 64, effects=tuple(effects),
    )


def _verdict(workload: dict[str, Any], schedule: dict[str, Any],
             reports: list[dict[str, Any]], effects: list[AttributedEffect]) -> Any:
    history = compile_history(workload, schedule, reports,
                              _readback(effects, len(workload["trials"])))
    return check_history(history)


def test_clean_history_has_no_violations() -> None:
    verdict = _verdict(
        _workload(), _schedule([]),
        [_report(0, "committed"), _report(1, "committed")],
        [_effect(1, "0"), _effect(2, "1")],
    )
    assert verdict.violations == []
    assert verdict.diagnostics == []


def test_h1_counterexample_duplicate() -> None:
    verdict = _verdict(
        _workload(), _schedule([]),
        [_report(0, "committed"), _report(1, "committed")],
        [_effect(1, "0"), _effect(2, "0"), _effect(3, "0"), _effect(4, "1")],
    )
    assert verdict.count("H1-duplicate-effect") == 2  # n=3 ⇒ 2 excess entries


def test_h2_counterexample_orphan() -> None:
    verdict = _verdict(
        _workload(), _schedule([]),
        [_report(0, "committed"), _report(1, "committed")],
        [_effect(1, "0"), _effect(2, "1"), _effect(3, None, via="oob")],
    )
    assert verdict.count("H2-orphan-effect") == 1


def test_h3_counterexample_lost() -> None:
    verdict = _verdict(
        _workload(), _schedule([]),
        [_report(0, "committed"), _report(1, "committed")],
        [_effect(1, "0")],  # trial 1's legitimate effect is absent
    )
    assert verdict.count("H3-lost-legitimate-effect") == 1


def test_h4_h5_counterexamples_pre_dispatch_conditions() -> None:
    workload = _workload(
        flags={0: {"legitimate": False, "eligible_for_dispatch": False},
               1: {"legitimate": False, "eligible_for_dispatch": False}},
    )
    schedule = _schedule([
        {"trial_index": 0, "fault": "branch-cancellation", "anchor": "T_DISPATCH", "param": {}},
        {"trial_index": 1, "fault": "stale-authorization", "anchor": "T_DISPATCH", "param": {}},
    ])
    verdict = _verdict(
        workload, schedule,
        [_report(0, "committed"), _report(1, "committed")],
        [_effect(1, "0"), _effect(2, "1")],  # both effects should NOT exist
    )
    assert verdict.count("H4-effect-after-cancellation") == 1
    assert verdict.count("H5-unauthorized-effect") == 1


def test_h6_counterexample_false_suppression() -> None:
    verdict = _verdict(
        _workload(), _schedule([]),
        [_report(0, "suppressed", dispatched=False), _report(1, "committed")],
        [_effect(1, "1")],
    )
    assert verdict.count("H6-false-suppression") == 1
    # And the same absence also registers as lost (it IS lost).
    assert verdict.count("H3-lost-legitimate-effect") == 1


def test_h7_counterexample_claim_contradiction() -> None:
    verdict = _verdict(
        _workload(), _schedule([]),
        [
            _report(0, "committed", oracle_claim="unique"),
            _report(1, "failed", oracle_claim="absent"),
        ],
        [_effect(1, "0"), _effect(2, "0"), _effect(3, "1")],  # both claims wrong
    )
    assert verdict.count("H7-claim-contradiction") == 2


def test_h8_counterexample_effect_despite_pre_persist_crash() -> None:
    workload = _workload(
        flags={0: {"eligible_for_dispatch": False}},
    )
    schedule = _schedule([
        {"trial_index": 0, "fault": "crash-before-persist",
         "anchor": "T_FIRST_DURABLE", "param": {}},
    ])
    verdict = _verdict(
        workload, schedule,
        [_report(0, "arm-crashed", dispatched=False), _report(1, "committed")],
        [_effect(1, "0"), _effect(2, "1")],  # trial 0's effect must not exist
    )
    assert verdict.count("H8-effect-despite-pre-persist-crash") == 1
    # The journaling-gap diagnostic fires too: an effect exists although no
    # dispatch was recorded for the trial.
    assert any(
        d["kind"] == "effect-without-recorded-dispatch" for d in verdict.diagnostics
    )


def test_ambiguous_attribution_surfaces_as_diagnostic() -> None:
    verdict = _verdict(
        _workload(), _schedule([]),
        [_report(0, "committed"), _report(1, "committed")],
        [_effect(1, "0"), _effect(2, "1"), _effect(3, None, ambiguous=True)],
    )
    assert any(d["kind"] == "ambiguous-attribution" for d in verdict.diagnostics)
    assert verdict.count("H2-orphan-effect") == 1  # declined ⇒ counted as orphan


def test_cross_check_consistent_on_agreeing_oracles() -> None:
    workload = _workload()
    schedule = _schedule([])
    reports = [_report(0, "committed"), _report(1, "committed")]
    effects = [_effect(1, "0"), _effect(2, "0"), _effect(3, "1")]
    verdict = _verdict(workload, schedule, reports, effects)
    metrics = {
        "duplicate_effect_rate": {"numerator": 1, "denominator": 2, "value": 0.5, "mark": None},
        "orphaned_effect_rate": {"numerator": 0, "denominator": 3, "value": 0, "mark": None},
        "lost_legitimate_effect_rate": {
            "numerator": 0, "denominator": 2, "value": 0, "mark": None,
        },
        "false_suppression_rate": {"numerator": 0, "denominator": 2, "value": 0, "mark": None},
        "false_reconciliation_rate": {
            "numerator": None, "denominator": None, "value": None, "mark": "N/A-by-arm",
        },
    }
    assert cross_check_metrics(metrics, verdict, workload) == []


def test_cross_check_fires_on_doctored_metric() -> None:
    """THE differential guard: a metric pipeline that under-reports duplicates
    (the classic favorable-measurement bug) is caught by the independent
    history checker — and vice versa."""
    workload = _workload()
    schedule = _schedule([])
    reports = [_report(0, "committed"), _report(1, "committed")]
    effects = [_effect(1, "0"), _effect(2, "0"), _effect(3, "1")]
    verdict = _verdict(workload, schedule, reports, effects)
    doctored = {
        "duplicate_effect_rate": {"numerator": 0, "denominator": 2, "value": 0, "mark": None},
        "orphaned_effect_rate": {"numerator": 0, "denominator": 3, "value": 0, "mark": None},
        "lost_legitimate_effect_rate": {
            "numerator": 0, "denominator": 2, "value": 0, "mark": None,
        },
        "false_suppression_rate": {"numerator": 0, "denominator": 2, "value": 0, "mark": None},
        "false_reconciliation_rate": {
            "numerator": None, "denominator": None, "value": None, "mark": "N/A-by-arm",
        },
    }
    discrepancies = cross_check_metrics(doctored, verdict, workload)
    assert len(discrepancies) == 1
    assert "duplicate_effect_rate" in discrepancies[0]


def test_history_digest_is_stable_and_events_ordered() -> None:
    workload = _workload()
    schedule = _schedule([])
    reports = [_report(0, "committed"), _report(1, "committed")]
    readback = _readback([_effect(1, "0"), _effect(2, "1")])
    h1 = compile_history(workload, schedule, reports, readback)
    h2 = compile_history(workload, schedule, reports, readback)
    assert h1["history_digest"] == h2["history_digest"]
    event_ids = [e["event_id"] for e in h1["events"]]
    assert event_ids == sorted(event_ids)
    kinds = {e["kind"] for e in h1["events"]}
    assert "arm:outcome" in kinds and "destination:effect-created" in kinds
