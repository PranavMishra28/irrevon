"""Runtime taint canary (testing.md §4.1 leg B).

Conformance: master doc §12.1 row 1 — "Keys derive only from stable identifiers,
never model output (§7.2)" (M3), runtime leg: the registrar wraps model-argument
payloads in ModelTainted; any implicit consumption raises TaintViolation, and the
dispatched idempotency evidence must be reproducible from
(stable_ids, effect_type, scope, step) alone.
"""

from __future__ import annotations

import json
from typing import Any

import pytest
from hypothesis import given

from detent.contract import ModelTainted, TaintViolation, validate_intent_contract
from detent.identity import (
    derive_idempotency_key,
    derive_intent_id,
    derive_operation_id,
)
from tests.identity.test_properties import _contract_dict, st_model_payload


@given(st_model_payload())
def test_registration_path_never_consumes_taint(payload: dict[str, Any]) -> None:
    """Full validate→derive path with adversarial payloads: no TaintViolation
    anywhere in the key path, and evidence is reproducible from the identity
    members plus step alone."""
    stable_ids = {"order_id": "9410"}
    contract = validate_intent_contract(
        _contract_dict(stable_ids, "order.create", "acme-store/prod", payload)
    )
    intent_id = derive_intent_id(
        contract.stable_ids, contract.effect_type, contract.scope
    )
    key = derive_idempotency_key(derive_operation_id(intent_id, 0))
    # Reproducible from the identity members alone — independent recomputation.
    assert key == derive_intent_id(stable_ids, "order.create", "acme-store/prod") + ":0"


def test_tainted_container_explodes_on_consumption() -> None:
    tainted = ModelTainted({"stable_ids": {"order_id": "HIJACK"}})
    with pytest.raises(TaintViolation):
        str(tainted)
    with pytest.raises(TaintViolation):
        bytes(tainted)
    with pytest.raises(TaintViolation):
        iter(tainted)
    with pytest.raises(TaintViolation):
        len(tainted)
    with pytest.raises(TaintViolation):
        _ = tainted["stable_ids"]  # type: ignore[index]
    with pytest.raises(TaintViolation):
        "x" in tainted  # type: ignore[operator]  # noqa: B015
    with pytest.raises(TaintViolation):
        f"{tainted}"
    with pytest.raises(TaintViolation):
        dict(tainted)  # type: ignore[call-overload]
    with pytest.raises(TaintViolation):
        _ = tainted == {"a": 1}
    with pytest.raises(TaintViolation):
        hash(tainted)
    with pytest.raises(TaintViolation):
        bool(tainted)
    with pytest.raises(TypeError):
        json.dumps(tainted)


def test_validated_contract_wraps_parameters() -> None:
    contract = validate_intent_contract(
        _contract_dict({"order_id": "1"}, "t.create", "s", {"model": "payload"})
    )
    assert isinstance(contract.parameters, ModelTainted)
    with pytest.raises(TaintViolation):
        str(contract.parameters)
    # The one sanctioned exit, for the adapter boundary only.
    assert contract.parameters.reveal_for_adapter() == {"model": "payload"}
    # Evidence digest was computed at validation time, before wrapping.
    assert contract.parameters_digest.startswith("sha256:")
