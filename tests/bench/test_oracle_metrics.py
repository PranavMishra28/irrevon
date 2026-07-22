"""Oracle attribution + metric computation: known-answer, property, and
metamorphic coverage (the oracle is safety-critical — treat it adversarially)."""

from __future__ import annotations

from typing import Any

from hypothesis import given
from hypothesis import strategies as st

from irrevon.adapters.refdest import RefDest
from irrevon.bench.metrics import METRIC_NAMES, compute_metrics, metric_cell, na_cell
from irrevon.bench.oracle import build_intent_digest_map, read_back
from irrevon.identity import canonical_digest


def _workload(
    trials: list[dict[str, Any]], tier: str = "C2", fault: str = "response-lost"
) -> dict[str, Any]:
    return {
        "workload_id": "wl_test.unit",
        "cell": {
            "fault": fault,
            "effect_class": "IRREVERSIBLE",
            "tier": tier,
            "destination_kind": "refdest",
            "stratum": "S-REF",
        },
        "cell_id": f"{tier}/refdest/{fault}/IRREVERSIBLE",
        "trials": trials,
    }


def _trial(i: int, *, legitimate: bool = True, eligible: bool = True) -> dict[str, Any]:
    return {
        "trial_index": i,
        "stable_ids": {"order_id": str(1000 + i)},
        "effect_type": "order.create",
        "scope": "test",
        "parameters": {"line_items": [{"sku": f"SKU-{i}", "quantity": 1}]},
        "authority_ref": f"auth_{i}",
        "legitimate": legitimate,
        "eligible_for_dispatch": eligible,
    }


def _report(i: int, outcome: str, dispatched: bool = True, **detail: Any) -> dict[str, Any]:
    return {
        "trial_index": i,
        "arm_outcome": outcome,
        "dispatch_attempted": dispatched,
        "detail": detail,
    }


def test_oracle_attributes_by_payload_digest_not_client_ref() -> None:
    """Arm-neutrality: two arms with wildly different client refs produce the
    same attribution because the oracle keys on the fixture payload universe."""
    workload = _workload([_trial(0), _trial(1)])
    refdest = RefDest(seed=7, profile="C2")
    refdest.api_create("order.create", workload["trials"][0]["parameters"], "arm-a-ref-x")
    refdest.api_create("order.create", workload["trials"][0]["parameters"], "totally-different")
    refdest.api_create("order.create", workload["trials"][1]["parameters"], None)
    readback = read_back(refdest, workload, {})
    assert readback.per_intent_effect_counts == {"0": 2, "1": 1}
    assert readback.duplicate_excess() == 1
    assert readback.orphan_effect_count == 0


def test_oracle_counts_oob_effects_as_orphans() -> None:
    workload = _workload([_trial(0)])
    refdest = RefDest(seed=7, profile="C2")
    refdest.control_oob_create("order.create", {"rogue": True})
    readback = read_back(refdest, workload, {})
    assert readback.orphan_effect_count == 1
    assert readback.per_intent_effect_counts == {"0": 0}


def test_same_intent_variant_maps_to_base_intent() -> None:
    workload = _workload([_trial(0)])
    variant = {
        "variant_id": "var_test.1",
        "base_workload_id": "wl_test.unit",
        "base_trial_index": 0,
        "label": "same-intent",
        "stable_ids": {"order_id": "1000"},
        "parameters": {"items": [{"sku": "SKU-0", "qty": 1}]},
        "human_verdict": None,
    }
    variants = {"var_test.1": variant}
    digest_map = build_intent_digest_map(workload, variants)
    refdest = RefDest(seed=7, profile="C2")
    refdest.api_create("order.create", workload["trials"][0]["parameters"], "a")
    refdest.api_create("order.create", variant["parameters"], "b")
    readback = read_back(refdest, workload, variants)
    # Original + re-synthesized variant = TWO destination effects for ONE
    # intent: exactly one duplicate (the ACRFence failure, oracle-visible).
    assert readback.per_intent_effect_counts == {"0": 2}
    assert len(digest_map) == 2


def test_new_intent_variant_is_its_own_intent() -> None:
    workload = _workload([_trial(0)])
    variant = {
        "variant_id": "var_test.n",
        "base_workload_id": "wl_test.unit",
        "base_trial_index": 0,
        "label": "new-intent",
        "stable_ids": {"order_id": "9999"},
        "parameters": {"items": [{"sku": "OTHER", "qty": 5}]},
        "human_verdict": None,
    }
    digest_map = build_intent_digest_map(workload, {"var_test.n": variant})
    assert digest_map[canonical_digest(variant["parameters"])] == "variant:var_test.n"


# ── metric known answers ───────────────────────────────────────────────────────


class _FakeReadback:
    def __init__(self, counts: dict[str, int], orphans: int = 0) -> None:
        self.per_intent_effect_counts = counts
        self.orphan_effect_count = orphans
        self.total_effects = sum(counts.values()) + orphans
        self.readback_digest = "sha256:" + "0" * 64


def test_duplicate_rate_known_answer() -> None:
    workload = _workload([_trial(0), _trial(1), _trial(2), _trial(3)])
    reports = [_report(i, "committed") for i in range(4)]
    readback = _FakeReadback({"0": 1, "1": 3, "2": 1, "3": 2})
    metrics = compute_metrics(
        workload, reports, readback, ambiguity_concept=True, classifies=False  # type: ignore[arg-type]
    )
    # Excess = (3−1) + (2−1) = 3 over 4 eligible intents.
    assert metrics["duplicate_effect_rate"] == {
        "numerator": 3, "denominator": 4, "value": 0.75, "mark": None,
    }
    assert metrics["false_reconciliation_rate"] == na_cell("N/A-by-arm")


def test_lost_and_suppression_known_answer() -> None:
    workload = _workload([_trial(0), _trial(1), _trial(2, legitimate=False, eligible=False)])
    reports = [
        _report(0, "committed"),
        _report(1, "suppressed"),
        _report(2, "suppressed", dispatched=False),
    ]
    readback = _FakeReadback({"0": 1, "1": 0, "2": 0})
    metrics = compute_metrics(
        workload, reports, readback, ambiguity_concept=False, classifies=False  # type: ignore[arg-type]
    )
    # Trial 1 is legitimate, suppressed, and absent → false suppression 1/2.
    assert metrics["false_suppression_rate"]["numerator"] == 1
    assert metrics["false_suppression_rate"]["denominator"] == 2
    # Trial 1 also counts lost (legitimate intended, absent): 1/2.
    assert metrics["lost_legitimate_effect_rate"]["numerator"] == 1
    # Trial 2 is NOT legitimate: its absence penalizes nothing.
    assert metrics["unresolved_ambiguous_rate"] == na_cell("N/A-by-arm")


def test_zero_denominator_reports_na_never_zero() -> None:
    workload = _workload(
        [_trial(0, legitimate=False, eligible=False)], fault="branch-cancellation"
    )
    reports = [_report(0, "suppressed", dispatched=False)]
    readback = _FakeReadback({"0": 0})
    metrics = compute_metrics(
        workload, reports, readback, ambiguity_concept=False, classifies=False  # type: ignore[arg-type]
    )
    assert metrics["duplicate_effect_rate"] == na_cell("N/A")
    assert metrics["orphaned_effect_rate"] == na_cell("N/A")


def test_c1_expected_null_and_c3_fixture_truth_marks() -> None:
    workload_c1 = _workload([_trial(0)], tier="C1", fault="response-lost")
    workload_c3 = _workload([_trial(0)], tier="C3", fault="response-lost")
    reports = [_report(0, "committed")]
    readback = _FakeReadback({"0": 1})
    m1 = compute_metrics(workload_c1, reports, readback, ambiguity_concept=True, classifies=False)  # type: ignore[arg-type]
    m3 = compute_metrics(workload_c3, reports, readback, ambiguity_concept=True, classifies=False)  # type: ignore[arg-type]
    assert m1["duplicate_effect_rate"]["mark"] == "expected-null"
    assert m3["lost_legitimate_effect_rate"]["mark"] == "fixture-truth-only"
    assert m3["orphaned_effect_rate"]["mark"] == "fixture-truth-only"


def test_false_reconciliation_scores_wrong_claims() -> None:
    workload = _workload([_trial(0), _trial(1)])
    reports = [
        _report(0, "committed", oracle_claim="unique"),
        _report(1, "failed", oracle_claim="absent"),
    ]
    readback = _FakeReadback({"0": 2, "1": 0})  # claim 'unique' is WRONG (n=2)
    metrics = compute_metrics(
        workload, reports, readback, ambiguity_concept=True, classifies=True  # type: ignore[arg-type]
    )
    assert metrics["false_reconciliation_rate"] == {
        "numerator": 1, "denominator": 2, "value": 0.5, "mark": None,
    }


def test_compensation_na_when_none_attempted() -> None:
    workload = _workload([_trial(0)])
    metrics = compute_metrics(
        workload, [_report(0, "committed")], _FakeReadback({"0": 1}),  # type: ignore[arg-type]
        ambiguity_concept=True, classifies=False,
    )
    assert metrics["compensation_correctness"] == na_cell("N/A")


@given(
    counts=st.lists(st.integers(min_value=0, max_value=5), min_size=1, max_size=12),
)
def test_metamorphic_adding_a_duplicate_never_lowers_the_rate(counts: list[int]) -> None:
    """Metamorphic property: injecting one more destination effect for any
    intent can never DECREASE the duplicate rate."""
    trials = [_trial(i) for i in range(len(counts))]
    workload = _workload(trials)
    reports = [_report(i, "committed") for i in range(len(counts))]
    base_counts = {str(i): c for i, c in enumerate(counts)}
    base = compute_metrics(
        workload, reports, _FakeReadback(dict(base_counts)),  # type: ignore[arg-type]
        ambiguity_concept=True, classifies=False,
    )["duplicate_effect_rate"]
    bumped_counts = dict(base_counts)
    bumped_counts["0"] = bumped_counts["0"] + 1
    bumped = compute_metrics(
        workload, reports, _FakeReadback(bumped_counts),  # type: ignore[arg-type]
        ambiguity_concept=True, classifies=False,
    )["duplicate_effect_rate"]
    base_value = base["value"] if base["value"] is not None else 0.0
    bumped_value = bumped["value"] if bumped["value"] is not None else 0.0
    assert bumped_value >= base_value


def test_metric_names_cover_the_result_schema() -> None:
    from irrevon.contract import load_schema

    schema = load_schema("bench-result.schema.json")
    assert set(schema["properties"]["metrics"]["required"]) == set(METRIC_NAMES)


def test_metric_cell_never_divides_by_zero() -> None:
    assert metric_cell(0, 0)["mark"] == "N/A"
    assert metric_cell(3, 4)["value"] == 0.75
