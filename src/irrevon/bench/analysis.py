"""Statistical-analysis pipeline + machine-readable comparison output (§5).

Two layers, kept deliberately separate:

1. **Descriptive comparison** (`build_comparison`): per-(arm, cell) rates with
   Wilson intervals, validity/replacement accounting (§6 reporting), and an
   environment-drift check — the machine-readable output CI systems consume
   (format tag ``irrevonbench/comparison/v1``).
2. **Confirmatory machinery** (`confirmatory_machinery`): the mechanical §5.3
   kill rule + §5.4 superiority rule. Every scientific parameter (equivalence
   margin δ, worst-cell gate, alphas) is a REQUIRED argument — they are §0.1
   human freeze parameters and this code refuses to default them. Pre-freeze,
   the machinery runs only on synthetic fixtures (tests/bench) and every output
   carries ``confirmatory: false`` — the §0 checklist item "analysis code for
   §5 written against synthetic data" is exactly this module.

The kill rule implemented verbatim (preregistration §5.3): fires iff for EVERY
primary metric (a) TOST equivalence at δ vs the preselected composite, OR
(b) the composite is significantly better than R (one-sided paired t,
α = 0.05); AND (c) no confirmatory cell shows the composite worse than R by ≥
the worst-cell gate. Failing (c) yields "inconclusive with a localized
signal" — never a kill and never a win. Neither superiority nor kill ⇒
inconclusive (§5.8), reported as limbo, never as survival.
"""

from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from irrevon.bench import HARNESS_VERSION
from irrevon.bench.formats import validate_document
from irrevon.bench.stats import (
    holm_bonferroni,
    one_sided_p,
    paired_t,
    sign_flip_permutation_p,
    tost_paired,
    wilson_interval,
)

__all__ = [
    "PRIMARY_METRICS",
    "RunRecord",
    "build_comparison",
    "confirmatory_machinery",
    "load_runs",
    "render_markdown",
]

PRIMARY_METRICS = (
    "duplicate_effect_rate",
    "orphaned_effect_rate",
    "lost_legitimate_effect_rate",
)


@dataclass(frozen=True)
class RunRecord:
    run_dir: Path
    manifest: dict[str, Any]
    result: dict[str, Any]

    @property
    def arm_id(self) -> str:
        return str(self.manifest["arm"]["arm_id"])

    @property
    def cell_id(self) -> str:
        return str(self.manifest["plan"]["cell_id"])

    @property
    def replicate(self) -> int:
        return int(self.manifest["plan"]["replicate_index"])

    @property
    def valid(self) -> bool:
        return bool(self.result["validity"]["status"] == "VALID")


def load_runs(runs_dir: Path) -> list[RunRecord]:
    """Load every completed run under ``runs_dir`` (manifest + result),
    schema-validating both. INVALID runs are loaded too — they are retained,
    marked, and REPORTED (§6), never skipped silently."""
    records = []
    for manifest_path in sorted(runs_dir.glob("*/run-manifest.json")):
        result_path = manifest_path.parent / "result.json"
        if not result_path.is_file():
            continue  # incomplete: finalized by the runner at resume time
        manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
        result = json.loads(result_path.read_text(encoding="utf-8"))
        validate_document(manifest)
        validate_document(result)
        records.append(RunRecord(manifest_path.parent, manifest, result))
    return records


def _metric_value(record: RunRecord, metric: str) -> float | None:
    cell = record.result["metrics"][metric]
    value = cell["value"]
    return None if value is None else float(value)


def build_comparison(records: list[RunRecord]) -> dict[str, Any]:
    """The machine-readable cross-arm comparison document."""
    valid = [r for r in records if r.valid]
    arms = sorted({r.arm_id for r in valid})
    cells = sorted({r.cell_id for r in valid})
    env_digests = {r.manifest["environment_digest"] for r in records}

    table: dict[str, Any] = {}
    for arm in arms:
        table[arm] = {}
        for cell in cells:
            cell_records = [r for r in valid if r.arm_id == arm and r.cell_id == cell]
            if not cell_records:
                continue
            metrics_block: dict[str, Any] = {}
            for metric in (
                *PRIMARY_METRICS,
                "false_suppression_rate",
                "unresolved_ambiguous_rate",
                "false_reconciliation_rate",
                "human_review_rate",
                "compensation_correctness",
            ):
                marks = {r.result["metrics"][metric]["mark"] for r in cell_records}
                numer = sum(
                    r.result["metrics"][metric]["numerator"] or 0 for r in cell_records
                )
                denom = sum(
                    r.result["metrics"][metric]["denominator"] or 0 for r in cell_records
                )
                if denom == 0:
                    metrics_block[metric] = {
                        "pooled_rate": None,
                        "wilson_95": None,
                        "marks": sorted(m for m in marks if m),
                    }
                    continue
                low, high = wilson_interval(numer, denom)
                metrics_block[metric] = {
                    "pooled_rate": numer / denom,
                    "numerator": numer,
                    "denominator": denom,
                    "wilson_95": [low, high],
                    "marks": sorted(m for m in marks if m),
                }
            table[arm][cell] = {
                "replicates": sorted(r.replicate for r in cell_records),
                "metrics": metrics_block,
            }

    invalid = [r for r in records if not r.valid]
    return {
        "format": "irrevonbench/comparison/v1",
        "harness_version": HARNESS_VERSION,
        "confirmatory": False,
        "labels": ["non-confirmatory", "mechanism-test", "synthetic-destination"],
        "arms": arms,
        "cells": cells,
        "run_accounting": {
            "registered": len(records),
            "valid": len(valid),
            "invalid": len(invalid),
            "invalid_run_ids": sorted(r.result["run_id"] for r in invalid),
            "replacements": sorted(
                r.result["run_id"]
                for r in records
                if r.manifest["replaces_run_id"] is not None
            ),
        },
        "environment_drift": {
            "distinct_environments": len(env_digests),
            "drifted": len(env_digests) > 1,
        },
        "table": table,
        "interpretation_note": (
            "Rates are fault-conditional client-side reconciliation outcomes "
            "against declared destination contracts under injected faults on a "
            "SYNTHETIC reference destination; they say nothing about "
            "destination reliability, model quality, end-to-end task success, "
            "or any confirmatory hypothesis (preregistration §4 note; runs are "
            "pre-Stage-A mechanism tests)."
        ),
    }


def _per_seed_pooled(
    records: list[RunRecord], arm: str, cells: list[str], metric: str
) -> dict[int, float]:
    """§5.2 estimand: per replicate (seed), the unweighted mean of the cell
    rates. Requires every named cell present and numeric for that seed."""
    out: dict[int, float] = {}
    by_rep: dict[int, dict[str, float]] = {}
    for r in records:
        if r.arm_id != arm or not r.valid or r.cell_id not in cells:
            continue
        value = _metric_value(r, metric)
        if value is None:
            continue
        by_rep.setdefault(r.replicate, {})[r.cell_id] = value
    for rep, cell_values in by_rep.items():
        if set(cell_values) == set(cells):
            out[rep] = sum(cell_values.values()) / len(cells)
    return out


def confirmatory_machinery(
    records: list[RunRecord],
    *,
    cells: list[str],
    reference_arm: str,
    composite_arm: str,
    b5_arm: str,
    margin: float,
    worst_cell_gate_pp: float,
    alpha_superiority: float = 0.025,
    alpha_kill: float = 0.05,
) -> dict[str, Any]:
    """The mechanical F1/F2 verdict computation (§5.3/§5.4/§5.7/§5.8).

    ``margin`` and ``worst_cell_gate_pp`` are §0.1 HUMAN parameters — there is
    deliberately no default. The output always carries ``confirmatory: false``
    until the Stage-B freeze exists; pre-freeze it may only ever be fed
    synthetic fixtures (the §0 checklist mechanization)."""
    per_metric: dict[str, Any] = {}
    superiority_ps: dict[str, float] = {}

    for metric in PRIMARY_METRICS:
        pooled_r = _per_seed_pooled(records, reference_arm, cells, metric)
        pooled_c = _per_seed_pooled(records, composite_arm, cells, metric)
        pooled_b5 = _per_seed_pooled(records, b5_arm, cells, metric)
        shared = sorted(set(pooled_r) & set(pooled_c) & set(pooled_b5))
        if len(shared) < 2:
            per_metric[metric] = {"verdict": "insufficient-seeds", "seeds": shared}
            continue
        diffs_c = [pooled_r[s] - pooled_c[s] for s in shared]
        diffs_b5 = [pooled_r[s] - pooled_b5[s] for s in shared]

        estimate = paired_t(diffs_c)
        tost = tost_paired(diffs_c, margin=margin, alpha=alpha_kill)
        p_sup_c = one_sided_p(diffs_c)  # H1: R − composite < 0
        p_sup_b5 = one_sided_p(diffs_b5)
        p_comp_better = one_sided_p([-d for d in diffs_c])  # composite < R
        perm_p = sign_flip_permutation_p(diffs_c)

        # Worst-cell gate (§5.3 c): descriptive per-cell estimates only.
        worst_cell_fired = False
        worst_cell_detail = {}
        for cell in cells:
            r_vals = [
                v for v in (
                    _metric_value(r, metric)
                    for r in records
                    if r.arm_id == reference_arm and r.valid and r.cell_id == cell
                ) if v is not None
            ]
            c_vals = [
                v for v in (
                    _metric_value(r, metric)
                    for r in records
                    if r.arm_id == composite_arm and r.valid and r.cell_id == cell
                ) if v is not None
            ]
            if not r_vals or not c_vals:
                continue
            gap = (sum(c_vals) / len(c_vals)) - (sum(r_vals) / len(r_vals))
            worst_cell_detail[cell] = gap
            if gap >= worst_cell_gate_pp:
                worst_cell_fired = True

        # IUT superiority: must reject against BOTH comparators (§5.4).
        superiority_ps[metric] = max(p_sup_c, p_sup_b5)

        kill_component = tost.equivalent or (p_comp_better < alpha_kill)
        per_metric[metric] = {
            "seeds": shared,
            "estimate": {
                "mean_diff": estimate.mean_diff,
                "ci95": [estimate.ci_low, estimate.ci_high],
                "t": estimate.t_stat,
                "df": estimate.df,
                "permutation_p_two_sided": perm_p,
                "permutation_floor": 1.0 / (2 ** len(shared)),
            },
            "tost": {
                "margin": margin,
                "equivalent": tost.equivalent,
                "p_lower": tost.p_lower,
                "p_upper": tost.p_upper,
            },
            "composite_significantly_better": p_comp_better < alpha_kill,
            "kill_component_holds": kill_component,
            "worst_cell": {
                "gate_pp": worst_cell_gate_pp,
                "fired": worst_cell_fired,
                "per_cell_composite_minus_r": worst_cell_detail,
            },
            "superiority_p_iut": superiority_ps[metric],
        }

    computable = [m for m in PRIMARY_METRICS if "estimate" in per_metric.get(m, {})]
    all_kill_components = computable and all(
        per_metric[m]["kill_component_holds"] for m in computable
    ) and len(computable) == len(PRIMARY_METRICS)
    any_worst_cell = any(
        per_metric[m]["worst_cell"]["fired"] for m in computable
    )
    if all_kill_components and not any_worst_cell:
        kill_verdict = "kill-fires"
    elif all_kill_components and any_worst_cell:
        kill_verdict = "inconclusive-with-localized-signal"
    else:
        kill_verdict = "kill-does-not-fire"

    # F1 family: Holm within the 3 IUT superiority p-values (§5.7).
    holm = (
        holm_bonferroni(superiority_ps, alpha=alpha_superiority)
        if superiority_ps
        else {}
    )
    for metric in computable:
        superior = holm.get(metric, False)
        if superior:
            verdict = "superiority"
        elif kill_verdict == "kill-fires":
            verdict = "equivalence-kill"
        elif kill_verdict == "inconclusive-with-localized-signal":
            verdict = "inconclusive-with-localized-signal"
        else:
            verdict = "inconclusive"  # limbo is limbo, never survival (§5.8)
        per_metric[metric]["verdict"] = verdict
        per_metric[metric]["holm_rejected"] = superior

    return {
        "format": "irrevonbench/verdict/v1",
        "confirmatory": False,
        "labels": ["non-confirmatory", "mechanism-test"],
        "parameters": {
            "margin": margin,
            "worst_cell_gate_pp": worst_cell_gate_pp,
            "alpha_superiority": alpha_superiority,
            "alpha_kill": alpha_kill,
            "cells": cells,
            "reference_arm": reference_arm,
            "composite_arm": composite_arm,
            "b5_arm": b5_arm,
        },
        "per_metric": per_metric,
        "kill_rule": kill_verdict,
        "note": (
            "Verdicts computed pre-freeze are mechanism tests on synthetic "
            "data; they carry NO confirmatory weight (preregistration §0). "
            "The holdout split governs the publish threshold at M7 (§7)."
        ),
    }


def render_markdown(comparison: dict[str, Any]) -> str:
    """Human-readable companion to the machine-readable comparison."""
    lines = [
        "# IrrevonBench comparison (non-confirmatory mechanism run)",
        "",
        f"Harness {comparison['harness_version']} · labels: "
        + ", ".join(comparison["labels"]),
        "",
        f"Runs: {comparison['run_accounting']['registered']} registered · "
        f"{comparison['run_accounting']['valid']} valid · "
        f"{comparison['run_accounting']['invalid']} INVALID (retained)",
        "",
    ]
    for arm in comparison["arms"]:
        lines.append(f"## Arm {arm}")
        for cell, block in sorted(comparison["table"].get(arm, {}).items()):
            dup = block["metrics"]["duplicate_effect_rate"]
            lost = block["metrics"]["lost_legitimate_effect_rate"]

            def fmt(cell_block: dict[str, Any]) -> str:
                if cell_block["pooled_rate"] is None:
                    return "N/A (" + ",".join(cell_block["marks"]) + ")"
                low, high = cell_block["wilson_95"]
                marks = f" [{','.join(cell_block['marks'])}]" if cell_block["marks"] else ""
                return (
                    f"{cell_block['pooled_rate']:.3f} "
                    f"(95% Wilson {low:.3f}–{high:.3f}){marks}"
                )

            lines.append(f"- `{cell}`: duplicate {fmt(dup)} · lost {fmt(lost)}")
        lines.append("")
    lines.append(comparison["interpretation_note"])
    lines.append("")
    return "\n".join(lines)
