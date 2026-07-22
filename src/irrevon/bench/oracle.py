"""Destination-state oracle — authoritative read-back (preregistration §3, §8.2).

The oracle owns two things no arm may touch:

1. The refdest **truth API** (``control_state`` — the ground-truth dump), and
2. the fixture-truth mapping from destination effects to true intents.

Attribution is arm-neutral by construction and robust to destination-side
normalization/enrichment (ADR-0032). Two mechanisms, in order:

- **Dispatched-payload digest** (primary): refdest records the canonical
  digest of the payload it stored; the oracle precomputes digest → intent
  over the fixture's known payload universe (original parameters + every
  frozen variant). Exact, but breaks when the destination stores a
  normalized/enriched representation — as real APIs do.
- **Stable-id projection** (fallback): the fixture's stable-id VALUES are
  projected against every string value found in the destination's stored
  ground-truth payload. An effect attributes to an intent iff exactly one
  intent's full stable-id value set is present; ambiguous projections are
  never guessed — they are counted and surfaced (`ambiguous_attributions`),
  because a wrong attribution is worse than a declared one.

Neither mechanism reads any arm-chosen reference (client_ref, keys), so no
arm can influence the denominator or the attribution it is judged by.

Import discipline: ``irrevon.bench.arms`` MUST NOT import this module
(import-linter contract — the no-hidden-oracle-data rule).
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from irrevon.adapters.refdest import RefDest
from irrevon.identity import canonical_digest

__all__ = [
    "AttributedEffect",
    "OracleReadback",
    "attribute_effects",
    "build_intent_digest_map",
    "read_back",
]


@dataclass(frozen=True)
class AttributedEffect:
    """One destination ground-truth effect with its oracle attribution."""

    destination_ref: str
    request_seq: int
    created_at: str
    via: str
    intent_key: str | None  # trial index (str), "variant:<id>", or None
    attributed_by: str | None  # "digest" | "stable-id-projection" | None
    ambiguous: bool  # projection matched >1 intent (never guessed)


@dataclass(frozen=True)
class OracleReadback:
    """One authoritative post-run destination read-back."""

    total_effects: int
    per_intent_effect_counts: dict[str, int]  # trial_index (str) → n effects
    orphan_effect_count: int
    ambiguous_attributions: int
    readback_digest: str  # digest over the sanitized read-back rows
    effects: tuple[AttributedEffect, ...] = field(default=(), compare=False)

    def duplicate_excess(self) -> int:
        return sum(max(0, n - 1) for n in self.per_intent_effect_counts.values())


def build_intent_digest_map(
    workload: dict[str, Any], variants_by_id: dict[str, dict[str, Any]]
) -> dict[str, str]:
    """payload canonical digest → intent key over the fixture payload universe."""
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


def _string_values(value: object, out: set[str]) -> None:
    if isinstance(value, str):
        out.add(value)
    elif isinstance(value, dict):
        for v in value.values():
            _string_values(v, out)
    elif isinstance(value, list):
        for v in value:
            _string_values(v, out)


def _projection_targets(
    workload: dict[str, Any], variants_by_id: dict[str, dict[str, Any]]
) -> list[tuple[str, frozenset[str]]]:
    """(intent_key, required stable-id value set) — same-intent variants share
    the base intent's identity by definition; new-intent variants carry their
    own stable ids."""
    targets = [
        (str(t["trial_index"]), frozenset(t["stable_ids"].values()))
        for t in workload["trials"]
    ]
    for variant in variants_by_id.values():
        if variant["base_workload_id"] != workload["workload_id"]:
            continue
        if variant["label"] == "new-intent":
            targets.append(
                (f"variant:{variant['variant_id']}", frozenset(variant["stable_ids"].values()))
            )
    return targets


def attribute_effects(
    refdest: RefDest,
    workload: dict[str, Any],
    variants_by_id: dict[str, dict[str, Any]],
) -> list[AttributedEffect]:
    """Attribute every ground-truth destination effect (digest first,
    stable-id projection second, never a guess)."""
    digest_map = build_intent_digest_map(workload, variants_by_id)
    targets = _projection_targets(workload, variants_by_id)
    attributed: list[AttributedEffect] = []
    for effect in refdest.control_state():
        intent_key: str | None = None
        attributed_by: str | None = None
        ambiguous = False
        if effect.get("via") != "oob":
            intent_key = digest_map.get(effect["payload_digest"])
            if intent_key is not None:
                attributed_by = "digest"
            else:
                values: set[str] = set()
                _string_values(effect.get("payload"), values)
                matches = [key for key, ids in targets if ids and ids <= values]
                if len(matches) == 1:
                    intent_key = matches[0]
                    attributed_by = "stable-id-projection"
                elif len(matches) > 1:
                    ambiguous = True  # counted, surfaced, never guessed
        attributed.append(
            AttributedEffect(
                destination_ref=effect["destination_ref"],
                request_seq=int(effect.get("request_seq", 0)),
                created_at=effect["created_at"],
                via=str(effect.get("via", "api")),
                intent_key=intent_key,
                attributed_by=attributed_by,
                ambiguous=ambiguous,
            )
        )
    return attributed


def read_back(
    refdest: RefDest, workload: dict[str, Any], variants_by_id: dict[str, dict[str, Any]]
) -> OracleReadback:
    """Read the destination's ground truth back and attribute every effect."""
    effects = attribute_effects(refdest, workload, variants_by_id)
    per_intent: dict[str, int] = {
        str(trial["trial_index"]): 0 for trial in workload["trials"]
    }
    orphans = 0
    ambiguous = 0
    sanitized_rows = []
    for effect in effects:
        if effect.intent_key is None:
            orphans += 1
        else:
            per_intent[effect.intent_key] = per_intent.get(effect.intent_key, 0) + 1
        if effect.ambiguous:
            ambiguous += 1
        sanitized_rows.append(
            {
                "destination_ref": effect.destination_ref,
                "request_seq": effect.request_seq,
                "created_at": effect.created_at,
                "attributed_intent": effect.intent_key,
                "attributed_by": effect.attributed_by,
            }
        )
    return OracleReadback(
        total_effects=len(effects),
        per_intent_effect_counts=per_intent,
        orphan_effect_count=orphans,
        ambiguous_attributions=ambiguous,
        readback_digest=canonical_digest(sanitized_rows),
        effects=tuple(effects),
    )
