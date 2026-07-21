"""Intent Registrar semantics — re-registration member classes (RFC-002 §1).

Pure decision logic: given the persisted record's members and a newly validated
contract carrying the SAME identity tuple, decide conflict vs authority-refresh
vs parameter-variant vs plain replay. The ledger (T-102) executes the decision
transactionally; an in-memory registrar drives the T-101 tests.

Member classes (RFC-002 §1 table):

- ``stable_ids``/``effect_type``/``scope`` — identity: same tuple, same record.
- ``effect_class``/``adapter_id``/``branch_ref`` — must match; mismatch is an
  ``identity_conflict`` citing the stored record (a re-synthesized retry with a
  different effect class or destination is a red flag, not a dedup case).
- ``authority_ref``+``stamped_at`` — a fresh authority alone is accepted as an
  authority-refresh append (the sanctioned path legitimate redispatch needs).
- ``parameters``/``event_time`` — non-identity payload: divergence is recorded
  as a parameter-variant row (canonical digest, evidence only) and the call
  returns the existing ``effect_id`` with ``replayed: true``.
"""

from __future__ import annotations

from dataclasses import dataclass

from irrevon.contract.validation import IntentContract
from irrevon.errors import IdentityConflict
from irrevon.identity import canonical_digest, derive_intent_id

__all__ = ["PersistedIdentity", "ReregistrationDecision", "adjudicate_reregistration"]


@dataclass(frozen=True, slots=True)
class PersistedIdentity:
    """The stored record's members relevant to re-registration adjudication."""

    effect_id: str
    effect_class: str
    adapter_id: str
    branch_ref: str | None
    authority_ref: str
    stamped_at: str
    parameters_digest: str
    event_time: str | None


@dataclass(frozen=True, slots=True)
class ReregistrationDecision:
    """Outcome of adjudicating a same-identity re-registration."""

    effect_id: str
    replayed: bool
    authority_refresh: bool
    parameter_variant_digest: str | None


def adjudicate_reregistration(
    stored: PersistedIdentity, incoming: IntentContract
) -> ReregistrationDecision:
    """Apply the RFC-002 §1 member-class table. Raises ``IdentityConflict`` on
    a must-match mismatch; never mutates anything."""
    incoming_id = derive_intent_id(
        incoming.stable_ids, incoming.effect_type, incoming.scope
    )
    if incoming_id != stored.effect_id:
        raise ValueError(
            "adjudicate_reregistration called with a different identity tuple"
        )

    mismatches: dict[str, dict[str, str | None]] = {}
    if incoming.effect_class != stored.effect_class:
        mismatches["effect_class"] = {
            "stored": stored.effect_class,
            "incoming": incoming.effect_class,
        }
    if incoming.adapter_id != stored.adapter_id:
        mismatches["adapter_id"] = {
            "stored": stored.adapter_id,
            "incoming": incoming.adapter_id,
        }
    if incoming.branch_ref != stored.branch_ref:
        mismatches["branch_ref"] = {
            "stored": stored.branch_ref,
            "incoming": incoming.branch_ref,
        }
    if mismatches:
        raise IdentityConflict(
            "same identity tuple re-registered with different must-match members",
            details={
                "effect_id": stored.effect_id,
                "mismatches": mismatches,
                "stored_record_digest": canonical_digest(
                    {
                        "effect_id": stored.effect_id,
                        "effect_class": stored.effect_class,
                        "adapter_id": stored.adapter_id,
                        "branch_ref": stored.branch_ref,
                    }
                ),
            },
        )

    variant_digest: str | None = None
    if (
        incoming.parameters_digest != stored.parameters_digest
        or incoming.event_time != stored.event_time
    ):
        variant_digest = incoming.parameters_digest

    authority_refresh = (
        incoming.authority_ref != stored.authority_ref
        or incoming.stamped_at != stored.stamped_at
    )

    return ReregistrationDecision(
        effect_id=stored.effect_id,
        replayed=True,
        authority_refresh=authority_refresh,
        parameter_variant_digest=variant_digest,
    )
