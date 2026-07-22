"""Causal effect histories — compilation, invariant checking, cross-checking.

The Jepsen/Elle move applied to agent effects (lineage credited in ADR-0032
and docs/benchmark.md): instead of trusting a single final-state count, every
run compiles a **history** — the partial order of client-side operations (per
trial, in arm-action order) and destination-side effects (in the destination's
authoritative request order) — and a checker verifies named, polynomial-time
invariants over it.

Two distinct roles, deliberately separated:

1. **Behavioral invariants (H1–H8)** — violations ARE the measured anomalies
   (duplicate effect, orphan, lost-legitimate, effect-after-cancellation,
   unauthorized effect, false suppression, claim contradiction,
   effect-despite-crash-before-persist). H4/H5/H8 are supplementary
   diagnostics beyond the preregistration §4 metric table: they are reported
   per run, labeled, and NEVER pooled into §4 metrics or confirmatory
   analysis (adding a confirmatory metric is a preregistration change, not a
   harness change).
2. **The differential cross-check** — the §4 metrics (computed independently
   in ``irrevon.bench.metrics`` from read-back counts) must EQUAL the
   corresponding invariant-violation counts computed here from the compiled
   history. Divergence means one of the two oracles is wrong — the runner
   classifies that run harness-INVALID (independently proven harness
   corruption, §6). Neither oracle can drift silently.

Everything here consumes ground truth the arms can never see (import-linter
forbids ``irrevon.bench.arms`` → this module).
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from irrevon.bench.oracle import OracleReadback
from irrevon.identity import canonical_digest

__all__ = [
    "HISTORY_FORMAT",
    "HistoryVerdict",
    "check_history",
    "compile_history",
    "cross_check_metrics",
]

HISTORY_FORMAT = "irrevonbench/history/v1"

# Behavioral invariants (each checkable in one linear pass over the history).
INVARIANTS = (
    "H1-duplicate-effect",          # >1 destination effect for one intent
    "H2-orphan-effect",             # effect with no attributable fixture intent
    "H3-lost-legitimate-effect",    # legitimate intended effect absent at end
    "H4-effect-after-cancellation", # effect for a branch-cancelled trial
    "H5-unauthorized-effect",       # effect for a stale-authority trial
    "H6-false-suppression",         # arm blocked a legitimate effect that is absent
    "H7-claim-contradiction",       # arm's settle claim contradicts ground truth
    "H8-effect-despite-pre-persist-crash",  # crash-before-persist must be effect-free
)


@dataclass
class HistoryVerdict:
    violations: list[dict[str, Any]] = field(default_factory=list)
    diagnostics: list[dict[str, Any]] = field(default_factory=list)

    def count(self, invariant: str) -> int:
        return sum(1 for v in self.violations if v["invariant"] == invariant)


def compile_history(
    workload: dict[str, Any],
    schedule: dict[str, Any],
    trial_reports: list[dict[str, Any]],
    readback: OracleReadback,
) -> dict[str, Any]:
    """Compile one run's history document (irrevonbench/history/v1).

    Partial-order encoding: client events carry ``(trial_index, op_seq)``
    (total order within a trial — the arm's own action sequence); destination
    events carry ``destination_seq`` (the destination's authoritative request
    order). A client dispatch happens-before the destination effect its
    request created; that edge is recoverable from the attribution plus the
    request order and does not need to be stored per-event.
    """
    injections = {i["trial_index"]: i for i in schedule["injections"]}
    events: list[dict[str, Any]] = []
    event_id = 0

    def add(actor: str, kind: str, trial_index: int | None, **detail: Any) -> None:
        nonlocal event_id
        events.append(
            {
                "event_id": event_id,
                "actor": actor,
                "kind": kind,
                "trial_index": trial_index,
                **detail,
            }
        )
        event_id += 1

    for report in trial_reports:
        trial_index = report["trial_index"]
        injection = injections.get(trial_index)
        if injection is not None:
            add(
                "harness", f"fault:{injection['fault']}", trial_index,
                anchor=injection["anchor"],
            )
        op_seq = 0
        for entry in report.get("detail", {}).get("log", []):
            action = str(entry.get("action", "unknown"))
            sanitized = {
                k: v for k, v in entry.items()
                if k in ("action", "outcome", "lifecycle", "deny_check", "result",
                         "client_ref", "transport_outcome", "same_effect_id",
                         "replayed", "at", "reason", "branch_ref")
            }
            add("arm", f"arm:{action}", trial_index, op_seq=op_seq, detail=sanitized)
            op_seq += 1
        add(
            "arm", "arm:outcome", trial_index,
            outcome=report["arm_outcome"],
            dispatch_attempted=report["dispatch_attempted"],
            oracle_claim=report.get("detail", {}).get("oracle_claim"),
        )

    for effect in readback.effects:
        add(
            "destination", "destination:effect-created",
            int(effect.intent_key) if effect.intent_key is not None
            and effect.intent_key.isdigit() else None,
            destination_seq=effect.request_seq,
            destination_ref=effect.destination_ref,
            intent_key=effect.intent_key,
            attributed_by=effect.attributed_by,
            ambiguous=effect.ambiguous,
            via=effect.via,
        )

    trials_truth = {
        str(t["trial_index"]): {
            "legitimate": t["legitimate"],
            "eligible_for_dispatch": t["eligible_for_dispatch"],
            "fault": injections.get(t["trial_index"], {}).get("fault"),
        }
        for t in workload["trials"]
    }
    history = {
        "format": HISTORY_FORMAT,
        "workload_id": workload["workload_id"],
        "cell_id": workload["cell_id"],
        "replicate_index": workload["replicate_index"],
        "trials_truth": trials_truth,
        "events": events,
    }
    history["history_digest"] = canonical_digest(
        {k: v for k, v in history.items() if k != "history_digest"}
    )
    return history


def check_history(history: dict[str, Any]) -> HistoryVerdict:
    """One linear pass; every violation names its invariant, subject, and the
    event ids that evidence it."""
    verdict = HistoryVerdict()
    truth: dict[str, dict[str, Any]] = history["trials_truth"]
    events: list[dict[str, Any]] = history["events"]

    effect_events: dict[str, list[dict[str, Any]]] = {}
    orphan_events: list[dict[str, Any]] = []
    outcome_by_trial: dict[str, dict[str, Any]] = {}
    for event in events:
        if event["kind"] == "destination:effect-created":
            key = event.get("intent_key")
            if key is None:
                orphan_events.append(event)
            else:
                effect_events.setdefault(str(key), []).append(event)
        elif event["kind"] == "arm:outcome":
            outcome_by_trial[str(event["trial_index"])] = event

    def violate(invariant: str, subject: str, evidence: list[int], note: str) -> None:
        verdict.violations.append(
            {"invariant": invariant, "subject": subject, "evidence_event_ids": evidence,
             "note": note}
        )

    # H1: one violation per EXCESS effect for an intent (n − 1 entries).
    for key, evs in sorted(effect_events.items()):
        for extra in evs[1:]:
            violate(
                "H1-duplicate-effect", key,
                [evs[0]["event_id"], extra["event_id"]],
                f"{len(evs)} destination effects exist for one intent",
            )

    # H2: unattributable effects.
    for event in orphan_events:
        violate(
            "H2-orphan-effect", event.get("destination_ref", "?"),
            [event["event_id"]],
            "destination effect with no corresponding fixture intent",
        )

    for key, t in sorted(truth.items()):
        n_effects = len(effect_events.get(key, []))
        outcome = outcome_by_trial.get(key, {})
        fault = t.get("fault")

        # H3: legitimate intended effect absent at run end.
        if t["legitimate"] and t["eligible_for_dispatch"] and n_effects == 0:
            violate(
                "H3-lost-legitimate-effect", key,
                [outcome["event_id"]] if outcome else [],
                "legitimate intended effect absent at read-back",
            )
        # H4/H5: pre-dispatch conditions must yield zero effects.
        if fault == "branch-cancellation" and n_effects > 0:
            violate(
                "H4-effect-after-cancellation", key,
                [e["event_id"] for e in effect_events[key]],
                "effect exists although the branch was cancelled before dispatch",
            )
        if fault == "stale-authorization" and n_effects > 0:
            violate(
                "H5-unauthorized-effect", key,
                [e["event_id"] for e in effect_events[key]],
                "effect exists although authority had expired before dispatch",
            )
        # H6: arm blocked a legitimate effect and it is genuinely absent.
        if (
            t["legitimate"] and t["eligible_for_dispatch"]
            and outcome.get("outcome") == "suppressed" and n_effects == 0
        ):
            violate(
                "H6-false-suppression", key, [outcome["event_id"]],
                "legitimate effect blocked by the arm and absent at read-back",
            )
        # H7: the arm's settle claim contradicts ground truth.
        claim = outcome.get("oracle_claim")
        if claim == "unique" and n_effects != 1:
            violate(
                "H7-claim-contradiction", key, [outcome["event_id"]],
                f"arm claimed exactly-one; ground truth has {n_effects}",
            )
        if claim == "absent" and n_effects != 0:
            violate(
                "H7-claim-contradiction", key, [outcome["event_id"]],
                f"arm claimed absent; ground truth has {n_effects}",
            )
        # H8: crash-before-persist is provably effect-free.
        if fault == "crash-before-persist" and n_effects > 0:
            violate(
                "H8-effect-despite-pre-persist-crash", key,
                [e["event_id"] for e in effect_events[key]],
                "effect exists although the process died before any durable write",
            )
        # Diagnostic: effect exists but the journal recorded no dispatch.
        if n_effects > 0 and outcome and not outcome.get("dispatch_attempted"):
            verdict.diagnostics.append(
                {
                    "kind": "effect-without-recorded-dispatch",
                    "subject": key,
                    "note": "destination effect exists but the journal recorded "
                            "no dispatch attempt — journaling gap or attribution error",
                }
            )

    for event in events:
        if event["kind"] == "destination:effect-created" and event.get("ambiguous"):
            verdict.diagnostics.append(
                {
                    "kind": "ambiguous-attribution",
                    "subject": event.get("destination_ref", "?"),
                    "note": "stable-id projection matched multiple intents; "
                            "attribution declined (counted as orphan)",
                }
            )
    return verdict


def cross_check_metrics(
    metrics: dict[str, dict[str, Any]],
    verdict: HistoryVerdict,
    workload: dict[str, Any],
) -> list[str]:
    """The differential guard: §4 metric numerators (read-back counting) must
    equal the corresponding invariant-violation counts (history checking).
    Returns discrepancy descriptions; any entry ⇒ harness-INVALID."""
    eligible = {
        str(t["trial_index"]) for t in workload["trials"] if t["eligible_for_dispatch"]
    }
    discrepancies: list[str] = []

    def expect(metric: str, expected: int) -> None:
        cell = metrics[metric]
        if cell["numerator"] is None:
            if expected != 0:
                discrepancies.append(
                    f"{metric}: metric is N/A but the history checker found {expected}"
                )
            return
        if cell["numerator"] != expected:
            discrepancies.append(
                f"{metric}: metric numerator {cell['numerator']} != "
                f"history-checker count {expected}"
            )

    h1_eligible = sum(
        1 for v in verdict.violations
        if v["invariant"] == "H1-duplicate-effect" and v["subject"] in eligible
    )
    expect("duplicate_effect_rate", h1_eligible)
    expect("orphaned_effect_rate", verdict.count("H2-orphan-effect"))
    expect("lost_legitimate_effect_rate", verdict.count("H3-lost-legitimate-effect"))
    expect("false_suppression_rate", verdict.count("H6-false-suppression"))
    if metrics["false_reconciliation_rate"]["numerator"] is not None:
        expect("false_reconciliation_rate", verdict.count("H7-claim-contradiction"))
    return discrepancies
