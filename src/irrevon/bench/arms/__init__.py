"""Benchmark arms — the systems under test (baseline ladder B0–B7 + R).

Separation rule (owner directive + preregistration anti-cheating discipline):
benchmark logic (fixtures, faults, oracle, metrics) lives OUTSIDE this package;
arms receive only what a real integration would receive — the trial's business
intent, the wire adapter, and the episode script. Arms never see oracle/truth
data (``irrevon.bench.arms`` importing ``irrevon.bench.oracle`` is an
import-linter violation), never see fixture labels (``legitimate`` /
``eligible_for_dispatch`` are stripped from the episode), and cannot detect
individual benchmark examples beyond what any production caller would see.

Every arm carries a machine-readable spec: exact version, configuration digest,
retry behavior, model (where relevant), and KNOWN DEVIATIONS from the ideal
operationalization — recorded, never hidden (preregistration §8; MLPerf-style
system description discipline).
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import Any

from irrevon.identity import canonical_digest

__all__ = [
    "ArmDriver",
    "ArmSpec",
    "Episode",
    "TrialReport",
    "arm_manifest_entry",
]


@dataclass(frozen=True)
class ArmSpec:
    """The pinned system description of one arm."""

    arm_id: str
    description: str
    version: str
    retry_behavior: str
    operationalized: bool
    requires_postgres: bool = False
    ambiguity_concept: bool = False  # can the arm represent "outcome unknown"?
    classifies: bool = False  # does the arm make oracle-checkable claims?
    model: str | None = None
    known_deviations: tuple[str, ...] = ()
    stage_b_note: str | None = None
    config: dict[str, Any] = field(default_factory=dict)


@dataclass(frozen=True)
class Episode:
    """One trial as the arm sees it: the business intent plus the client-side
    fault script. Fixture ORACLE LABELS ARE DELIBERATELY ABSENT — an arm is
    handed exactly what a production integration would be handed."""

    trial_index: int
    stable_ids: dict[str, str]
    effect_type: str
    effect_class: str
    scope: str
    parameters: dict[str, Any]
    authority_ref: str
    fault: str | None  # the 7 preregistration kinds, or None (clean trial)
    retries: int  # identical-retry budget the scaffold grants on ambiguity
    resynth_parameters: dict[str, Any] | None  # frozen variant payload, if any
    resynth_stable_ids: dict[str, str] | None
    authority_expired: bool  # stale-authorization condition (T_DISPATCH)
    branch_cancelled: bool  # branch-cancellation condition (T_DISPATCH)
    branch_ref: str | None


@dataclass
class TrialReport:
    """What the arm reports back — its own belief, scored later against the
    oracle (never by the arm itself)."""

    trial_index: int
    arm_outcome: str  # bench-result.schema.json trial enum
    dispatch_attempted: bool
    detail: dict[str, Any] = field(default_factory=dict)


class ArmDriver(ABC):
    """Driver lifecycle: one instance per (cell, replicate, arm) unit."""

    spec: ArmSpec

    @abstractmethod
    def begin_unit(self, unit_seed: int) -> None:
        """Fresh arm-side state for one unit (journals, caches, databases)."""

    @abstractmethod
    def run_episode(self, episode: Episode) -> TrialReport:
        """Execute one trial per the episode script."""

    @abstractmethod
    def end_unit(self) -> None:
        """Release arm-side resources; report nothing."""


def arm_manifest_entry(spec: ArmSpec, declaration_digest: str | None) -> dict[str, Any]:
    """The run-manifest ``arm`` object for a spec (bench-run-manifest schema)."""
    return {
        "arm_id": spec.arm_id,
        "description": spec.description,
        "version": spec.version,
        "config_digest": canonical_digest(spec.config),
        "retry_behavior": spec.retry_behavior,
        "model": spec.model,
        "prompt_scaffold_digest": None,
        "capability_declaration_digest": declaration_digest,
        "known_deviations": list(spec.known_deviations),
        # Deterministic driver arms have no model budget; Extended-track
        # LLM-embedded subjects must fill the full budget block at Stage-B.
        "budget": None,
    }
