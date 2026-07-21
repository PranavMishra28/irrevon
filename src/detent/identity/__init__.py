"""Pure identity derivation — RFC-001 §1 byte-level procedure (ADR-0020, proposed).

The least reversible decision in the slice: ``intent_id`` is the SHA-256 over the
RFC 8785 (JCS) canonical bytes of the identity tuple ``{effect_type, scope,
stable_ids}``; ``operation_id = intent_id ':' step``; idempotency evidence derives
ONLY from ``operation_id``.

Module discipline (RFC-002 §14): pure — no I/O, no clock, no intra-engine imports.
Enforced by the import-linter contract in pyproject.toml. Its only inputs are the
three identity members plus the ledger-allocated step; no derivation path reads
model output (master doc §12.1 row 1; conformance-tested in tests/identity/).
"""

from __future__ import annotations

import hashlib
import re
from collections.abc import Mapping
from typing import Final

import rfc8785

__all__ = [
    "INTENT_ID_RE",
    "OPERATION_ID_RE",
    "canonical_bytes",
    "canonical_digest",
    "derive_idempotency_key",
    "derive_intent_id",
    "derive_operation_id",
    "identity_tuple_bytes",
]

INTENT_ID_RE: Final = re.compile(r"^[0-9a-f]{64}$")
OPERATION_ID_RE: Final = re.compile(r"^[0-9a-f]{64}:(0|[1-9][0-9]*)$")


def canonical_bytes(value: object) -> bytes:
    """RFC 8785 (JCS) canonical UTF-8 bytes of a JSON-representable value.

    Encoder is the pinned ``rfc8785`` package (ADR-0013), guarded by the committed
    cross-implementation conformance vectors in tests/identity/vectors/.
    """
    # rfc8785 types its input as a recursive JSON union; callers pass validated
    # JSON-representable values, and non-representable ones raise at encode time.
    return rfc8785.dumps(value)  # type: ignore[arg-type]


def canonical_digest(value: object) -> str:
    """``sha256:<hex>`` digest over the JCS canonical bytes (evidence digests)."""
    return "sha256:" + hashlib.sha256(canonical_bytes(value)).hexdigest()


def _require_opaque_str(name: str, value: str) -> str:
    # Exactly `str` — a str subclass could smuggle tainted or non-canonical content
    # through the derivation path (testing.md §4.1 leg B).
    if type(value) is not str:
        raise TypeError(f"{name} must be str, got {type(value).__name__}")
    if not value:
        raise ValueError(f"{name} must be non-empty")
    return value


def identity_tuple_bytes(
    stable_ids: Mapping[str, str], effect_type: str, scope: str
) -> bytes:
    """Canonical JCS bytes of the identity tuple (RFC-001 §1 items 1-2).

    Stable-id values are opaque strings, hashed exactly as supplied — no case
    folding, no normalization. Absent optional members are omitted, never null.
    """
    _require_opaque_str("effect_type", effect_type)
    _require_opaque_str("scope", scope)
    if not stable_ids:
        raise ValueError("stable_ids must contain at least one identifier")
    checked: dict[str, str] = {}
    for key, value in stable_ids.items():
        _require_opaque_str("stable_ids key", key)
        _require_opaque_str(f"stable_ids[{key!r}]", value)
        checked[key] = value
    return canonical_bytes(
        {"effect_type": effect_type, "scope": scope, "stable_ids": checked}
    )


def derive_intent_id(
    stable_ids: Mapping[str, str], effect_type: str, scope: str
) -> str:
    """``intent_id`` = lowercase-hex SHA-256 over the canonical identity tuple."""
    return hashlib.sha256(identity_tuple_bytes(stable_ids, effect_type, scope)).hexdigest()


def derive_operation_id(intent_id: str, step: int) -> str:
    """``operation_id = intent_id ':' step`` (RFC-001 §1 item 4).

    ``step`` is allocated by the ledger (RFC-002 §1) — never by the model.
    """
    if not INTENT_ID_RE.match(intent_id):
        raise ValueError("intent_id must be a 64-char lowercase hex digest")
    if not isinstance(step, int) or isinstance(step, bool) or step < 0:
        raise ValueError("step must be a non-negative integer")
    return f"{intent_id}:{step}"


def derive_idempotency_key(operation_id: str) -> str:
    """Idempotency evidence derives ONLY from ``operation_id`` (RFC-001 §1 item 4).

    The core key IS the operation id; adapters map it onto the destination
    mechanism (e.g. a deterministic UUIDv5 for C1 headers) without adding inputs.
    """
    if not OPERATION_ID_RE.match(operation_id):
        raise ValueError("operation_id must match '<64-hex>:<step>'")
    return operation_id
