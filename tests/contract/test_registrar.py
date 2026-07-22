"""Registrar re-registration semantics — the RFC-002 §1 member-class table.

T-101 acceptance edge cases: same identity tuple + different effect_class →
identity_conflict citing the stored record; different parameters → same
effect_id with a recorded variant digest.
"""

from __future__ import annotations

from typing import Any

import pytest

from irrevon.contract import (
    PersistedIdentity,
    adjudicate_reregistration,
    validate_intent_contract,
)
from irrevon.errors import IdentityConflict
from irrevon.identity import derive_intent_id


def _raw(**overrides: Any) -> dict[str, Any]:
    raw: dict[str, Any] = {
        "schema_version": "1",
        "stable_ids": {"order_id": "9410", "customer_ref": "C-0007"},
        "effect_type": "order.create",
        "effect_class": "IRREVERSIBLE",
        "scope": "acme-store/prod",
        "adapter_id": "refdest-c2",
        "parameters": {"line_items": [{"sku": "SKU-1", "quantity": 2}]},
        "authority_ref": "auth_approved_task_18",
        "stamped_at": "2026-07-21T00:00:00Z",
    }
    raw.update(overrides)
    return raw


def _persist(raw: dict[str, Any]) -> PersistedIdentity:
    contract = validate_intent_contract(raw)
    return PersistedIdentity(
        effect_id=derive_intent_id(
            contract.stable_ids, contract.effect_type, contract.scope
        ),
        effect_class=contract.effect_class,
        adapter_id=contract.adapter_id,
        branch_ref=contract.branch_ref,
        authority_ref=contract.authority_ref,
        stamped_at=contract.stamped_at,
        parameters_digest=contract.parameters_digest,
        event_time=contract.event_time,
    )


def test_identical_reregistration_is_plain_replay() -> None:
    stored = _persist(_raw())
    decision = adjudicate_reregistration(stored, validate_intent_contract(_raw()))
    assert decision.effect_id == stored.effect_id
    assert decision.replayed is True
    assert decision.authority_refresh is False
    assert decision.parameter_variant_digest is None


@pytest.mark.parametrize(
    ("member", "value"),
    [
        ("effect_class", "REVERSIBLE"),
        ("adapter_id", "other-adapter"),
        ("branch_ref", "wf_branch_9"),
    ],
)
def test_must_match_member_mismatch_is_identity_conflict(
    member: str, value: str
) -> None:
    """RFC-002 §1: a re-synthesized retry with a different effect class or
    destination is a red flag, not a dedup case."""
    stored = _persist(_raw())
    incoming = validate_intent_contract(_raw(**{member: value}))
    with pytest.raises(IdentityConflict) as excinfo:
        adjudicate_reregistration(stored, incoming)
    assert excinfo.value.code == "identity_conflict"
    # The error cites the stored record.
    assert excinfo.value.details["effect_id"] == stored.effect_id
    assert member in excinfo.value.details["mismatches"]


def test_different_parameters_records_variant_same_effect_id() -> None:
    """Divergent parameters → same effect_id, replayed, variant digest recorded
    (evidence for the dedup deny, RFC-002 §4)."""
    stored = _persist(_raw())
    resynthesized = validate_intent_contract(
        _raw(parameters={"line_items": [{"sku": "SKU-1", "quantity": 3}], "note": "retry"})
    )
    decision = adjudicate_reregistration(stored, resynthesized)
    assert decision.effect_id == stored.effect_id
    assert decision.replayed is True
    assert decision.parameter_variant_digest == resynthesized.parameters_digest
    assert decision.parameter_variant_digest != stored.parameters_digest


def test_fresh_authority_is_refresh_append_not_conflict() -> None:
    """A fresh authority alone is the sanctioned authority-refresh path."""
    stored = _persist(_raw())
    refreshed = validate_intent_contract(
        _raw(authority_ref="auth_approved_task_22", stamped_at="2026-07-21T09:00:00Z")
    )
    decision = adjudicate_reregistration(stored, refreshed)
    assert decision.authority_refresh is True
    assert decision.parameter_variant_digest is None
    assert decision.effect_id == stored.effect_id


def test_event_time_divergence_is_variant_not_conflict() -> None:
    stored = _persist(_raw())
    incoming = validate_intent_contract(_raw(event_time="2026-07-20T18:04:09Z"))
    decision = adjudicate_reregistration(stored, incoming)
    assert decision.parameter_variant_digest is not None


def test_different_identity_tuple_is_a_caller_bug() -> None:
    stored = _persist(_raw())
    other = validate_intent_contract(_raw(stable_ids={"order_id": "9999"}))
    with pytest.raises(ValueError):
        adjudicate_reregistration(stored, other)
