"""Contract module — schema validation and registrar decision logic (RFC-002 §14).

This module handles raw model-shaped input; the identity module is forbidden
from importing it (import-linter contract in pyproject.toml).
"""

from irrevon.contract.registrar import (
    PersistedIdentity,
    ReregistrationDecision,
    adjudicate_reregistration,
)
from irrevon.contract.taint import ModelTainted, TaintViolation
from irrevon.contract.validation import (
    IntentContract,
    load_schema,
    validate_intent_contract,
)

__all__ = [
    "IntentContract",
    "ModelTainted",
    "PersistedIdentity",
    "ReregistrationDecision",
    "TaintViolation",
    "adjudicate_reregistration",
    "load_schema",
    "validate_intent_contract",
]
