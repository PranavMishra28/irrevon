"""Pinned RFC 8785 conformance vectors — the external oracle for the JCS encoder.

Conformance: master doc §12.1 row 1 — "Keys derive only from stable identifiers,
never model output (§7.2)" (M3), oracle leg: the canonicalizer is checked against
cross-implementation vectors (stack.md §4: byte-identical across Python/Node/Go/
Rust), not against our own implementation. If the pinned ``rfc8785`` package ever
drifts, these tests fail before any identity is mis-derived.
"""

import hashlib
import json
from pathlib import Path

import pytest

from detent.identity import canonical_bytes, derive_intent_id

VECTORS_DIR = Path(__file__).parent / "vectors"
EXPECTED = {
    k: v
    for k, v in json.loads(
        (VECTORS_DIR / "expected-digests.json").read_text(encoding="utf-8")
    ).items()
    if not k.startswith("_")
}

# Exact canonical bytes for the intent tuple, cross-verified in the T-000 spike.
V2_CANONICAL = (
    b'{"effect_type":"order.create","scope":"acme-store/prod",'
    b'"stable_ids":{"customer_ref":"C-0007","order_id":"9410"}}'
)


@pytest.mark.parametrize("vector_name", sorted(EXPECTED))
def test_vector_reproduces_byte_for_byte(vector_name: str) -> None:
    value = json.loads((VECTORS_DIR / vector_name).read_text(encoding="utf-8"))
    digest = hashlib.sha256(canonical_bytes(value)).hexdigest()
    assert digest == EXPECTED[vector_name], (
        f"pinned rfc8785 encoder no longer reproduces conformance vector "
        f"{vector_name}; STOP — vendor-or-implement is a human decision (T-101)"
    )


def test_intent_tuple_canonical_bytes_exact() -> None:
    value = json.loads((VECTORS_DIR / "v2-intent-tuple.json").read_text(encoding="utf-8"))
    assert canonical_bytes(value) == V2_CANONICAL


def test_key_order_invariance_on_pinned_vectors() -> None:
    v2 = json.loads((VECTORS_DIR / "v2-intent-tuple.json").read_text(encoding="utf-8"))
    v3 = json.loads(
        (VECTORS_DIR / "v3-key-order-scrambled.json").read_text(encoding="utf-8")
    )
    assert canonical_bytes(v2) == canonical_bytes(v3)


def test_derive_intent_id_matches_vector_digest() -> None:
    """intent_id over the v2 tuple must equal the cross-language digest —
    the derivation IS SHA-256 over those canonical bytes, nothing more."""
    intent_id = derive_intent_id(
        {"order_id": "9410", "customer_ref": "C-0007"}, "order.create", "acme-store/prod"
    )
    assert intent_id == EXPECTED["v2-intent-tuple.json"]
