"""Intent-contract schema validation — the trust boundary (master doc §6.3).

Reuses the canonical example suites in schemas/examples/ as fixtures: every
valid-*.json must validate; every invalid-*.json must be rejected with the
stable ``contract_invalid`` error code.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import pytest

from detent.contract import validate_intent_contract
from detent.errors import ContractInvalid

REPO_ROOT = Path(__file__).parent.parent.parent
EXAMPLES = REPO_ROOT / "schemas" / "examples" / "intent-contract"


def _load(path: Path) -> Any:
    return json.loads(path.read_text(encoding="utf-8"))


@pytest.mark.parametrize(
    "path", sorted(EXAMPLES.glob("valid-*.json")), ids=lambda p: p.name
)
def test_valid_examples_pass(path: Path) -> None:
    contract = validate_intent_contract(_load(path))
    assert contract.stable_ids


@pytest.mark.parametrize(
    "path", sorted(EXAMPLES.glob("invalid-*.json")), ids=lambda p: p.name
)
def test_invalid_examples_rejected(path: Path) -> None:
    with pytest.raises(ContractInvalid) as excinfo:
        validate_intent_contract(_load(path))
    assert excinfo.value.code == "contract_invalid"
    assert excinfo.value.details["errors"]


def test_no_stable_ids_rejected() -> None:
    """The Intent Registrar rejects intents lacking a stable identifier (§6.1)."""
    raw = _load(EXAMPLES / "valid-order-create.json")
    raw["stable_ids"] = {}
    with pytest.raises(ContractInvalid):
        validate_intent_contract(raw)


def test_null_stable_id_value_rejected() -> None:
    """Absent ≠ null: null is rejected by the schema (RFC-001 §1 item 2)."""
    raw = _load(EXAMPLES / "valid-order-create.json")
    raw["stable_ids"]["order_id"] = None
    with pytest.raises(ContractInvalid):
        validate_intent_contract(raw)


def test_undeclared_member_rejected() -> None:
    """additionalProperties is closed: undeclared members cannot ride along."""
    raw = _load(EXAMPLES / "valid-order-create.json")
    raw["model_generated_arguments"] = {"anything": True}
    with pytest.raises(ContractInvalid):
        validate_intent_contract(raw)


def test_non_object_rejected() -> None:
    with pytest.raises(ContractInvalid):
        validate_intent_contract(["not", "an", "object"])


def test_error_envelope_shape() -> None:
    """SDK errors follow the dx-api §1.3 envelope."""
    try:
        validate_intent_contract({})
    except ContractInvalid as err:
        envelope = err.to_envelope()
        assert envelope["schema_version"] == "1"
        assert envelope["error"]["code"] == "contract_invalid"
        assert envelope["error"]["retryable"] is False
        assert envelope["error"]["details"]["errors"]
    else:  # pragma: no cover
        pytest.fail("empty contract must be rejected")
