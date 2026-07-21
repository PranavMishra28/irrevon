"""Advisory module — the ADR-006 isolation seam ONLY (no classifier ships in
the first slice; T-104 scope).

Two enforced layers (RFC-002 §14):

1. **Import direction** — no authority module (ledger, gate, dispatcher,
   reconciler, recovery, resolution, sweep, api) imports this module; enforced
   by the import-linter contracts in pyproject.toml (direct AND indirect).
2. **Type level** — classifier output is the distinct
   :class:`ClassifierProposal` type that NO mutation API accepts; every
   mutation path additionally rejects payloads carrying the advisory marker
   (covers duck-typed / serialized-then-deserialized laundering).

The marker-based rejection lives in :func:`irrevon.errors.reject_advisory` so
authority modules can enforce layer 2 WITHOUT importing this module (which
would violate layer 1).
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from irrevon.errors import ADVISORY_MARKER

__all__ = ["ClassifierProposal"]


@dataclass(frozen=True, slots=True)
class ClassifierProposal:
    """Advisory output: a PROPOSAL, never a resolution. It has no code path to
    gate, resolve, or settle (master doc §6.3; conformance-tested)."""

    subject_effect_id: str | None
    proposed_action: str
    confidence: float
    rationale: str

    def to_payload(self) -> dict[str, Any]:
        """Serialized form — carries the advisory marker so a round-tripped
        proposal is still rejected by every mutation API."""
        return {
            ADVISORY_MARKER: True,
            "subject_effect_id": self.subject_effect_id,
            "proposed_action": self.proposed_action,
            "confidence": self.confidence,
            "rationale": self.rationale,
        }


_ = field  # keep dataclasses import surface stable for future proposal fields
