"""Run orchestration — write-ahead registration, resume, invalid-run rules.

Execution discipline (preregistration §6/§8):

- The run manifest is written FIRST (write-ahead): a run that dies pre-evidence
  still exists in the record.
- Duplicate execution is prevented mechanically: a slot with a completed result
  is never re-executed.
- An interrupted run (manifest without result) is finalized as harness-INVALID
  at resume time — retained and marked, never deleted — and re-run under a new
  run id with the SAME seed, at most twice per slot; a slot that cannot produce
  a valid run in three attempts is reported unresolved, never silently dropped.
- Harness-invalid is the ONLY invalid class; arm-attributable outcomes are
  VALID and scored.
- Confirmatory mode is an INTEGRITY REFUSAL (exit 4 at the CLI) until the
  human Stage-B freeze record exists in docs/registrations/stage-b-v1/ AND the
  fixtures are frozen. Nothing in this repository can flip that pre-freeze.
"""

from __future__ import annotations

import hashlib
import json
import time
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from irrevon.adapters.base import declarations_dir, load_declaration
from irrevon.adapters.refdest import RefDest, RefdestAdapter
from irrevon.bench import HARNESS_VERSION
from irrevon.bench.arms import ArmDriver, Episode, arm_manifest_entry
from irrevon.bench.arms.conventional import CONVENTIONAL_SPECS, make_conventional_driver
from irrevon.bench.arms.reference import REFERENCE_SPEC, ReferenceArm
from irrevon.bench.canonical import canonical_json_text
from irrevon.bench.environment import capture_environment
from irrevon.bench.formats import FixtureSet, validate_document
from irrevon.bench.history import check_history, compile_history, cross_check_metrics
from irrevon.bench.metrics import METRIC_NAMES, compute_metrics, na_cell
from irrevon.bench.oracle import read_back
from irrevon.bench.seeds import derive_seed
from irrevon.identity import canonical_digest

__all__ = [
    "ALL_ARM_IDS",
    "IntegrityRefusal",
    "UnitOutcome",
    "refuse_unless_confirmatory_allowed",
    "run_unit",
]

ALL_ARM_IDS = (*CONVENTIONAL_SPECS.keys(), "R")

_MAX_ATTEMPTS_PER_SLOT = 3  # original + at most two replacements (§6)


class IntegrityRefusal(RuntimeError):
    """Preregistration-integrity guard tripped; the CLI maps this to exit 4."""


def _repo_root() -> Path | None:
    for parent in Path(__file__).resolve().parents:
        if (parent / "pyproject.toml").is_file() and (parent / "docs").is_dir():
            return parent
    return None


def refuse_unless_confirmatory_allowed(
    fixture_set: FixtureSet, repo_root: Path | None = None
) -> None:
    """Confirmatory mode requires BOTH freeze registrations to pass full
    structural + hash-binding verification (ADR-0033): the registration must
    schema-validate, carry no REQUIRED-HUMAN sentinel, and bind the CURRENT
    preregistration bytes, analysis sources, fixture root, and holdout
    commitment. A directory's mere existence gates nothing."""
    from irrevon.bench.freeze import verify_freeze_registration

    root = repo_root or _repo_root()
    if root is None:
        raise IntegrityRefusal("confirmatory mode refused: repository root not found")
    for stage in ("A", "B"):
        verification = verify_freeze_registration(stage, root)
        if not verification.ok:
            raise IntegrityRefusal(
                f"confirmatory mode refused: Stage-{stage} freeze registration "
                "failed verification (preregistration §0 — freezing is a human "
                "act): " + "; ".join(verification.failures)
            )
    if fixture_set.manifest["freeze_status"] != "frozen":
        raise IntegrityRefusal(
            "confirmatory mode refused: fixture manifest is not frozen "
            f"(freeze_status={fixture_set.manifest['freeze_status']!r})"
        )


@dataclass
class UnitOutcome:
    run_id: str
    run_dir: Path
    status: str  # completed | skipped-duplicate | unresolved-slot
    validity: str | None = None
    note: str = ""


# ── fault → destination-side schedule mapping (client-side injection: the
#    destination drops a response ON CUE; everything else is enacted by the
#    episode script in the arm scaffold) ─────────────────────────────────────

_DESTINATION_FAULTED = {
    "response-lost",
    "crash-after-effect-before-response",
    "retry-storm",
    "semantic-resynthesis",
}


def _install_destination_fault(refdest: RefDest, fault: str, tier: str) -> None:
    if fault not in _DESTINATION_FAULTED:
        return
    op = "notify" if tier == "C3" else "create"
    refdest.control_schedule(
        [{"match": {"op": op}, "fault": "DROP_RESPONSE_AFTER_COMMIT", "once": True}]
    )


def _episode(
    workload: dict[str, Any],
    trial: dict[str, Any],
    injection: dict[str, Any] | None,
    variants_by_id: dict[str, dict[str, Any]],
) -> Episode:
    fault = injection["fault"] if injection else None
    param = injection["param"] if injection else {}
    resynth_parameters = None
    resynth_stable_ids = None
    if fault == "semantic-resynthesis":
        variant = variants_by_id[param["variant_id"]]
        resynth_parameters = dict(variant["parameters"])
        resynth_stable_ids = dict(variant["stable_ids"])
    branch_ref = (
        f"branch-{workload['workload_id']}-t{trial['trial_index']}"
        if fault == "branch-cancellation"
        else None
    )
    # Oracle labels (legitimate / eligible_for_dispatch) are DELIBERATELY not
    # copied into the episode: arms see only what production callers see.
    return Episode(
        trial_index=trial["trial_index"],
        stable_ids=dict(trial["stable_ids"]),
        effect_type=trial["effect_type"],
        effect_class=workload["cell"]["effect_class"],
        scope=trial["scope"],
        parameters=dict(trial["parameters"]),
        authority_ref=trial["authority_ref"],
        fault=fault,
        retries=int(param.get("retries", 1)),
        resynth_parameters=resynth_parameters,
        resynth_stable_ids=resynth_stable_ids,
        authority_expired=fault == "stale-authorization",
        branch_cancelled=fault == "branch-cancellation",
        branch_ref=branch_ref,
    )


def _make_driver(
    arm_id: str, adapter: RefdestAdapter, workdir: Path, admin_dsn: str | None
) -> ArmDriver:
    if arm_id == "R":
        if admin_dsn is None:
            raise IntegrityRefusal(
                "arm R requires a Postgres admin DSN (the reference engine is "
                "ledger-backed); pass --dsn or run the conventional arms only"
            )
        return ReferenceArm(adapter, admin_dsn)
    return make_conventional_driver(arm_id, adapter, workdir)


def _arm_spec(arm_id: str) -> Any:
    return REFERENCE_SPEC if arm_id == "R" else CONVENTIONAL_SPECS[arm_id]


def _slot_attempts(out_dir: Path, base_run_id: str) -> list[Path]:
    candidates = [out_dir / base_run_id] + [
        out_dir / f"{base_run_id}.r{n}" for n in range(2, _MAX_ATTEMPTS_PER_SLOT + 1)
    ]
    return [c for c in candidates if c.is_dir()]


def _write_json(path: Path, document: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(canonical_json_text(document), encoding="utf-8")


def _finalize_incomplete(run_dir: Path, labels: list[str]) -> None:
    """Mechanically classify an interrupted run (manifest, no result) as
    harness-INVALID — retained and marked, never deleted (§6)."""
    manifest = json.loads((run_dir / "run-manifest.json").read_text(encoding="utf-8"))
    result = {
        "format": "irrevonbench/result/v1",
        "run_id": manifest["run_id"],
        "run_manifest_digest": canonical_digest(manifest),
        "completed_at": "1970-01-01T00:00:00Z",
        "confirmatory": False,
        "labels": sorted(set(labels) | {"non-confirmatory"}),
        "validity": {
            "status": "INVALID",
            "invalid_class": "harness-corruption",
            "evidence": [
                "interrupted run: write-ahead manifest present, no result "
                "document; finalized mechanically at resume time (§6)"
            ],
        },
        "trials": [],
        "oracle_readback": {
            "performed": False,
            "readback_digest": None,
            "destination_effect_count": None,
            "per_intent_effect_counts": None,
            "orphan_effect_count": None,
            "ambiguous_attributions": None,
        },
        "metrics": {name: na_cell("N/A") for name in METRIC_NAMES},
        "evidence": {"bundle_dir": run_dir.as_posix(), "artifact_digests": {}},
        "residual_effects_after_cleanup": 0,
    }
    validate_document(result)
    _write_json(run_dir / "result.json", result)


def run_unit(
    fixture_set: FixtureSet,
    workload_id: str,
    arm_id: str,
    out_dir: Path,
    *,
    admin_dsn: str | None = None,
    confirmatory: bool = False,
    extra_labels: tuple[str, ...] = (),
    enrichment_quirk: bool = False,
) -> UnitOutcome:
    """Execute one (workload=cell×replicate, arm) unit with full §6/§8 discipline."""
    if confirmatory:
        refuse_unless_confirmatory_allowed(fixture_set)

    spec = _arm_spec(arm_id)
    if not spec.operationalized:
        raise IntegrityRefusal(
            f"arm {arm_id} is registered but not operationalized: {spec.stage_b_note}"
        )

    workload = fixture_set.workloads[workload_id]
    schedule = fixture_set.schedules[workload_id]
    variants_by_id = fixture_set.variants_by_id()
    labels = sorted(
        {"non-confirmatory", "mechanism-test", "synthetic-destination", *extra_labels}
    )

    arm_slug = arm_id.lower().replace("+", "-")
    base_run_id = f"run_{workload_id.removeprefix('wl_')}.{arm_slug}"

    # ── duplicate-execution prevention + resume (§6 slot discipline) ──────────
    attempts = _slot_attempts(out_dir, base_run_id)
    for attempt in attempts:
        result_path = attempt / "result.json"
        if result_path.is_file():
            result = json.loads(result_path.read_text(encoding="utf-8"))
            if result["validity"]["status"] == "VALID":
                return UnitOutcome(
                    run_id=result["run_id"], run_dir=attempt,
                    status="skipped-duplicate", validity="VALID",
                    note="completed VALID result already exists; re-execution refused",
                )
        elif (attempt / "run-manifest.json").is_file():
            _finalize_incomplete(attempt, labels)
    unit_started = time.monotonic()
    attempts = _slot_attempts(out_dir, base_run_id)
    completed_invalid = [
        a for a in attempts if (a / "result.json").is_file()
    ]
    if len(attempts) >= _MAX_ATTEMPTS_PER_SLOT:
        return UnitOutcome(
            run_id=base_run_id, run_dir=out_dir / base_run_id,
            status="unresolved-slot",
            note=f"slot exhausted {_MAX_ATTEMPTS_PER_SLOT} attempts without a "
                 "valid run; reported unresolved, never silently dropped (§6)",
        )
    attempt_no = len(attempts) + 1
    run_id = base_run_id if attempt_no == 1 else f"{base_run_id}.r{attempt_no}"
    replaces = completed_invalid[-1].name if completed_invalid else None
    run_dir = out_dir / run_id
    run_dir.mkdir(parents=True, exist_ok=False)

    # ── seed verification (mismatch ⇒ harness-INVALID, §6) ────────────────────
    master_seed = fixture_set.manifest["master_seed"]
    unit_seed = int(workload["seed"])
    seed_ok = master_seed is not None and (
        derive_seed(master_seed, workload["cell_id"], workload["replicate_index"])
        == unit_seed
    )

    # ── environment + destination + reset verification ────────────────────────
    environment = capture_environment()
    validate_document(environment)
    _write_json(run_dir / "environment.json", environment)

    tier = workload["cell"]["tier"]
    # enrichment_quirk: the destination stores a normalized/enriched
    # representation (real-API behavior); attribution must survive it via the
    # stable-id projection fallback (ADR-0032). Same fixtures, same episodes.
    refdest = RefDest(seed=unit_seed % 2**31, profile=tier, enrichment_quirk=enrichment_quirk)
    pre_state = refdest.control_state()
    reset_verified = pre_state == []

    declaration = load_declaration(
        declarations_dir() / f"refdest-{tier.lower()}.capability.json"
    )
    adapter = RefdestAdapter(f"refdest-{tier.lower()}", declaration, instance=refdest)

    variant_set_id = None
    for injection in schedule["injections"]:
        if "variant_id" in injection["param"]:
            variant = variants_by_id[injection["param"]["variant_id"]]
            for vs_id, vs in fixture_set.variant_sets.items():
                if variant in vs["variants"]:
                    variant_set_id = vs_id
                    break

    run_manifest = {
        "format": "irrevonbench/run-manifest/v1",
        "run_id": run_id,
        "created_at": environment["captured_at"],
        "harness_version": HARNESS_VERSION,
        "confirmatory": confirmatory,
        "plan": {
            "manifest_root_hash": fixture_set.manifest["root_hash"],
            "workload_id": workload_id,
            "schedule_id": schedule["schedule_id"],
            "variant_set_id": variant_set_id,
            "cell_id": workload["cell_id"],
            "replicate_index": workload["replicate_index"],
            "seed": workload["seed"],
            "trial_count": len(workload["trials"]),
        },
        "arm": arm_manifest_entry(spec, canonical_digest(declaration)),
        "environment_digest": canonical_digest(environment),
        "reset_verification": {
            "verified": reset_verified,
            "readback_digest": canonical_digest(pre_state),
        },
        "replaces_run_id": replaces,
    }
    validate_document(run_manifest)
    _write_json(run_dir / "run-manifest.json", run_manifest)  # write-ahead

    # ── harness-invalid short-circuits (the ONLY invalid class, §6) ───────────
    invalid_class = None
    invalid_evidence: list[str] = []
    if not seed_ok:
        invalid_class = "seed-mismatch"
        invalid_evidence.append(
            "workload seed does not match derive_seed(master_seed, cell_id, replicate)"
        )
    elif not reset_verified:
        invalid_class = "reset-verification-failed"
        invalid_evidence.append("destination state non-empty before the run")

    trial_reports: list[dict[str, Any]] = []
    full_reports: list[dict[str, Any]] = []  # detail incl. logs, for the history
    journal_path = run_dir / "journal.jsonl"
    if invalid_class is None:
        injections = {i["trial_index"]: i for i in schedule["injections"]}
        driver = _make_driver(arm_id, adapter, run_dir, admin_dsn)
        driver.begin_unit(unit_seed % 2**31)
        try:
            with journal_path.open("a", encoding="utf-8") as journal:
                for trial in workload["trials"]:
                    injection = injections.get(trial["trial_index"])
                    if injection is not None:
                        _install_destination_fault(refdest, injection["fault"], tier)
                    if injection is not None and injection["fault"] == "crash-before-persist":
                        # The process dies at T_FIRST_DURABLE before any durable
                        # write: the arm is never invoked; nothing may exist.
                        report_dict: dict[str, Any] = {
                            "trial_index": trial["trial_index"],
                            "arm_outcome": "arm-crashed",
                            "dispatch_attempted": False,
                            "detail": {"fault": "crash-before-persist"},
                        }
                        full_report = report_dict
                    else:
                        episode = _episode(workload, trial, injection, variants_by_id)
                        report = driver.run_episode(episode)
                        detail = {
                            k: v for k, v in report.detail.items() if k != "log"
                        }
                        report_dict = {
                            "trial_index": report.trial_index,
                            "arm_outcome": report.arm_outcome,
                            "dispatch_attempted": report.dispatch_attempted,
                            "detail": detail,
                        }
                        full_report = {**report_dict, "detail": dict(report.detail)}
                        journal.write(json.dumps(full_report, default=str) + "\n")
                    trial_reports.append(report_dict)
                    full_reports.append(full_report)
        finally:
            driver.end_unit()

    # ── oracle read-back + metrics + history cross-check (arm-independent) ────
    history_block: dict[str, Any] | None = None
    if invalid_class is None:
        readback = read_back(refdest, workload, variants_by_id)
        metrics = compute_metrics(
            workload,
            trial_reports,
            readback,
            ambiguity_concept=spec.ambiguity_concept,
            classifies=spec.classifies,
        )
        oracle_block = {
            "performed": True,
            "readback_digest": readback.readback_digest,
            "destination_effect_count": readback.total_effects,
            "per_intent_effect_counts": dict(readback.per_intent_effect_counts),
            "orphan_effect_count": readback.orphan_effect_count,
            "ambiguous_attributions": readback.ambiguous_attributions,
        }
        # Second, independent oracle pass: compile the causal history and
        # check the named invariants; the §4 metric numerators MUST agree
        # with the invariant-violation counts (differential guard, ADR-0032).
        history = compile_history(workload, schedule, full_reports, readback)
        verdict = check_history(history)
        _write_json(run_dir / "history.json", history)
        discrepancies = cross_check_metrics(metrics, verdict, workload)
        by_invariant: dict[str, int] = {}
        for violation in verdict.violations:
            by_invariant[violation["invariant"]] = (
                by_invariant.get(violation["invariant"], 0) + 1
            )
        history_block = {
            "history_digest": history["history_digest"],
            "violations_total": len(verdict.violations),
            "violations_by_invariant": by_invariant,
            "diagnostics_total": len(verdict.diagnostics),
            "cross_check": "consistent" if not discrepancies else "DIVERGENT",
        }
        _write_json(
            run_dir / "history-verdict.json",
            {
                "violations": verdict.violations,
                "diagnostics": verdict.diagnostics,
                "cross_check_discrepancies": discrepancies,
            },
        )
        if discrepancies:
            # Two independent oracles disagreeing is independently proven
            # harness corruption (§6) — never silently preferred one way.
            invalid_class = "harness-corruption"
            invalid_evidence.extend(
                ["metric/history-checker divergence:", *discrepancies]
            )
    else:
        metrics = {name: na_cell("N/A") for name in METRIC_NAMES}
        oracle_block = {
            "performed": False,
            "readback_digest": None,
            "destination_effect_count": None,
            "per_intent_effect_counts": None,
            "orphan_effect_count": None,
            "ambiguous_attributions": None,
        }

    artifact_digests = {"run_manifest": canonical_digest(run_manifest)}
    if journal_path.is_file():
        artifact_digests["journal"] = (
            "sha256:" + hashlib.sha256(journal_path.read_bytes()).hexdigest()
        )

    result = {
        "format": "irrevonbench/result/v1",
        "run_id": run_id,
        "run_manifest_digest": canonical_digest(run_manifest),
        "completed_at": capture_environment()["captured_at"],
        "confirmatory": confirmatory,
        "labels": labels,
        "validity": {
            "status": "VALID" if invalid_class is None else "INVALID",
            "invalid_class": invalid_class,
            "evidence": invalid_evidence,
        },
        "trials": trial_reports,
        "oracle_readback": oracle_block,
        "metrics": metrics,
        "evidence": {
            "bundle_dir": run_dir.as_posix(),
            "artifact_digests": artifact_digests,
        },
        "residual_effects_after_cleanup": 0,
        "wall_time_s": round(time.monotonic() - unit_started, 3),
    }
    if history_block is not None:
        result["history"] = history_block
    validate_document(result)
    _write_json(run_dir / "result.json", result)
    return UnitOutcome(
        run_id=run_id,
        run_dir=run_dir,
        status="completed",
        validity=result["validity"]["status"],
    )
