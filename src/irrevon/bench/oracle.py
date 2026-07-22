"""Destination-state oracle — authoritative read-back (preregistration §3, §8.2).

The oracle owns two things no arm may touch:

1. The refdest **truth API** (``control_state`` — the ground-truth dump), and
2. the fixture-truth mapping from destination effects to true intents.

Mapping is arm-neutral by construction: refdest records the canonical digest of
every dispatched payload; the oracle precomputes digest → intent over the
fixture's known payload universe (original parameters + every frozen variant),
so no arm-chosen client reference or key participates in attribution. Effects
whose payload digest is outside the fixture universe (e.g. out-of-band
injections) have no corresponding true intent — the arm-neutral ORPHANED
definition (§4).

Import discipline: ``irrevon.bench.arms`` MUST NOT import this module
(import-linter contract — the no-hidden-oracle-data rule).
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from irrevon.adapters.refdest import RefDest
from irrevon.identity import canonical_digest

__all__ = ["OracleReadback", "build_intent_digest_map", "read_back"]


@dataclass(frozen=True)
class OracleReadback:
    """One authoritative post-run destination read-back."""

    total_effects: int
    per_intent_effect_counts: dict[str, int]  # trial_index (str) → n effects
    orphan_effect_count: int
    readback_digest: str  # digest over the sanitized read-back rows

    def duplicate_excess(self) -> int:
        return sum(max(0, n - 1) for n in self.per_intent_effect_counts.values())


def build_intent_digest_map(
    workload: dict[str, Any], variants_by_id: dict[str, dict[str, Any]]
) -> dict[str, str]:
    """payload canonical digest → intent key (the trial index as a string).

    Covers every payload any compliant arm could dispatch for an intent: the
    original parameters plus every same-intent variant frozen for that trial.
    A new-intent variant maps to its own intent key (``variant:<id>``) — its
    effect is legitimate, not a duplicate of the base intent.
    """
    digest_map: dict[str, str] = {}
    workload_id = workload["workload_id"]
    for trial in workload["trials"]:
        digest_map[canonical_digest(trial["parameters"])] = str(trial["trial_index"])
    for variant in variants_by_id.values():
        if variant["base_workload_id"] != workload_id:
            continue
        key = (
            str(variant["base_trial_index"])
            if variant["label"] == "same-intent"
            else f"variant:{variant['variant_id']}"
        )
        digest_map.setdefault(canonical_digest(variant["parameters"]), key)
    return digest_map


def read_back(
    refdest: RefDest, workload: dict[str, Any], variants_by_id: dict[str, dict[str, Any]]
) -> OracleReadback:
    """Read the destination's ground truth and attribute every effect."""
    digest_map = build_intent_digest_map(workload, variants_by_id)
    effects = refdest.control_state()
    per_intent: dict[str, int] = {
        str(trial["trial_index"]): 0 for trial in workload["trials"]
    }
    orphans = 0
    sanitized_rows = []
    for effect in effects:
        intent_key = digest_map.get(effect["payload_digest"])
        if intent_key is None or effect.get("via") == "oob":
            orphans += 1
            attributed: str | None = None
        else:
            per_intent[intent_key] = per_intent.get(intent_key, 0) + 1
            attributed = intent_key
        sanitized_rows.append(
            {
                "destination_ref": effect["destination_ref"],
                "payload_digest": effect["payload_digest"],
                "created_at": effect["created_at"],
                "attributed_intent": attributed,
            }
        )
    return OracleReadback(
        total_effects=len(effects),
        per_intent_effect_counts=per_intent,
        orphan_effect_count=orphans,
        readback_digest=canonical_digest(sanitized_rows),
    )
