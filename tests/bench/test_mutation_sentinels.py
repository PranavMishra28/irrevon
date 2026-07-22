"""Mutation sentinels — curated mutants of the oracle/metrics/history/stats
code MUST be killed by the existing known-answer assertions.

Framework-free mutation testing (deliberate: a mutmut dependency was rejected
— three runtime deps is a feature): each sentinel applies one realistic,
favorable-looking source mutation to a COPY of the module, loads it under a
throwaway name, and asserts a specific known answer now FAILS. If a mutant
survives, the assertion suite has a hole exactly where a measurement bug
could hide — the test fails loudly and names it.
"""

from __future__ import annotations

import importlib.util
import sys
from pathlib import Path
from types import ModuleType
from typing import Any, ClassVar

import pytest

REPO = Path(__file__).resolve().parents[2]


def _load_mutant(rel_path: str, original: str, mutant: str, name: str) -> ModuleType:
    source_path = REPO / rel_path
    source = source_path.read_text(encoding="utf-8")
    assert source.count(original) == 1, (
        f"mutation anchor not unique in {rel_path}: {original!r} "
        f"(found {source.count(original)}) — update the sentinel"
    )
    mutated = source.replace(original, mutant)
    spec = importlib.util.spec_from_loader(name, loader=None, origin=str(source_path))
    assert spec is not None
    module = importlib.util.module_from_spec(spec)
    sys.modules[name] = module
    try:
        exec(compile(mutated, str(source_path), "exec"), module.__dict__)
    finally:
        sys.modules.pop(name, None)
    return module


def _metrics_inputs() -> tuple[dict[str, Any], list[dict[str, Any]], Any]:
    class FakeReadback:
        per_intent_effect_counts: ClassVar[dict[str, int]] = {"0": 3, "1": 1}
        orphan_effect_count = 1
        total_effects = 5
        readback_digest = "sha256:" + "0" * 64

    workload = {
        "workload_id": "wl_mut",
        "cell": {"fault": "response-lost", "effect_class": "IRREVERSIBLE",
                 "tier": "C2", "destination_kind": "refdest", "stratum": "S-REF"},
        "cell_id": "C2/refdest/response-lost/IRREVERSIBLE",
        "trials": [
            {"trial_index": 0, "legitimate": True, "eligible_for_dispatch": True},
            {"trial_index": 1, "legitimate": True, "eligible_for_dispatch": True},
        ],
    }
    reports = [
        {"trial_index": 0, "arm_outcome": "committed", "dispatch_attempted": True, "detail": {}},
        {"trial_index": 1, "arm_outcome": "committed", "dispatch_attempted": True, "detail": {}},
    ]
    return workload, reports, FakeReadback()


# Each row: (module path, original snippet, mutant snippet, description).
# Every mutation is the kind that would make Irrevon look BETTER or hide an
# anomaly — the direction the adversarial-measurement rule cares about.
_METRIC_MUTANTS = [
    (
        "src/irrevon/bench/metrics.py",
        "max(0, counts.get(str(t[\"trial_index\"]), 0) - 1) for t in eligible",
        "max(0, counts.get(str(t[\"trial_index\"]), 0) - 2) for t in eligible",
        "duplicate excess under-count (n-2 instead of n-1)",
    ),
    (
        "src/irrevon/bench/metrics.py",
        "if denominator <= 0:\n        return na_cell(\"N/A\")",
        "if denominator < 0:\n        return na_cell(\"N/A\")",
        "zero-denominator rule weakened (0/0 would compute)",
    ),
]


@pytest.mark.parametrize(("path", "original", "mutant", "why"), _METRIC_MUTANTS)
def test_metric_mutants_are_killed(path: str, original: str, mutant: str, why: str) -> None:
    module = _load_mutant(path, original, mutant, f"mutant_metrics_{hash(why) & 0xffff}")
    workload, reports, readback = _metrics_inputs()
    result = module.compute_metrics(
        workload, reports, readback, ambiguity_concept=True, classifies=False
    )
    healthy_duplicate = {"numerator": 2, "denominator": 2, "value": 1.0, "mark": None}
    if "denominator" in why:
        # Killed = any observable deviation: the healthy module returns the
        # marked N/A cell; this mutant divides by zero (an exception is a
        # kill) or would return a fabricated value.
        try:
            cell = module.metric_cell(0, 0)
        except ZeroDivisionError:
            return
        assert cell != {"numerator": None, "denominator": None, "value": None, "mark": "N/A"}, (
            f"SURVIVING MUTANT ({why}): the zero-denominator known answer did not kill it"
        )
    else:
        assert result["duplicate_effect_rate"] != healthy_duplicate, (
            f"SURVIVING MUTANT ({why}): the duplicate-rate known answer did not kill it"
        )


def test_oracle_mutant_guessing_ambiguity_is_killed() -> None:
    """Mutant: attribution 'guesses' the first match when projection is
    ambiguous — the exact never-guess rule ADR-0032 pinned."""
    module = _load_mutant(
        "src/irrevon/bench/oracle.py",
        "if len(matches) == 1:\n                    intent_key = matches[0]",
        "if len(matches) >= 1:\n                    intent_key = matches[0]",
        "mutant_oracle_guess",
    )
    from irrevon.adapters.refdest import RefDest

    trial = {
        "trial_index": 0,
        "stable_ids": {"order_id": "5555"},
        "parameters": {"order_id": "5555", "n": 1},
    }
    other = {
        "trial_index": 1,
        "stable_ids": {"order_id": "5555"},
        "parameters": {"order_id": "5555", "n": 2},
    }
    workload = {"workload_id": "wl_mut", "trials": [trial, other]}
    dest = RefDest(seed=7, profile="C2", enrichment_quirk=True)
    dest.api_create("order.create", trial["parameters"], "r0")
    readback = module.read_back(dest, workload, {})
    # The healthy oracle declines (ambiguous=1, orphan=1); the mutant assigns.
    assert not (
        readback.ambiguous_attributions == 1 and readback.orphan_effect_count == 1
    ), "SURVIVING MUTANT: ambiguity-guessing was not detected by the known answer"


def test_history_mutant_dropping_h1_is_killed() -> None:
    """Mutant: the checker starts tolerating one extra effect (evs[2:] instead
    of evs[1:]) — duplicates of exactly n=2 vanish from H1."""
    module = _load_mutant(
        "src/irrevon/bench/history.py",
        "for extra in evs[1:]:",
        "for extra in evs[2:]:",
        "mutant_history_h1",
    )
    history = {
        "trials_truth": {"0": {"legitimate": True, "eligible_for_dispatch": True, "fault": None}},
        "events": [
            {"event_id": 0, "kind": "arm:outcome", "trial_index": 0,
             "outcome": "committed", "dispatch_attempted": True},
            {"event_id": 1, "kind": "destination:effect-created", "trial_index": 0,
             "intent_key": "0", "destination_seq": 1},
            {"event_id": 2, "kind": "destination:effect-created", "trial_index": 0,
             "intent_key": "0", "destination_seq": 2},
        ],
    }
    verdict = module.check_history(history)
    assert verdict.count("H1-duplicate-effect") != 1, (
        "SURVIVING MUTANT: an n=2 duplicate no longer raises H1 and nothing noticed"
    )
    # …and the differential guard in the REAL pipeline would catch this class
    # at run time anyway (metric/history divergence ⇒ INVALID) — both layers
    # exist so a paired mutation of both is required to cheat, which the
    # known-answer suites above make visible.


def test_stats_mutant_weakening_tost_is_killed() -> None:
    """Mutant: TOST declares equivalence when only ONE one-sided test rejects
    — the classic equivalence-inflation bug."""
    module = _load_mutant(
        "src/irrevon/bench/stats.py",
        "p_lower < alpha and p_upper < alpha",
        "p_lower < alpha or p_upper < alpha",
        "mutant_stats_tost",
    )
    sleep_diffs = [-1.2, -2.4, -1.3, -1.3, 0.0, -1.0, -1.8, -0.8, -4.6, -1.4]
    result = module.tost_paired(sleep_diffs, margin=0.5, alpha=0.05)
    assert result.equivalent is True, (
        "sentinel self-check: this mutant must flip the published TOSTER "
        "known answer (not equivalent) to True"
    )
    # The real module keeps the published answer:
    from irrevon.bench.stats import tost_paired

    assert tost_paired(sleep_diffs, margin=0.5, alpha=0.05).equivalent is False
