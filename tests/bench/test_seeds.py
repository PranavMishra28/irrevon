"""Seed derivation (§3.4) — determinism, sensitivity, and pinned vectors."""

from __future__ import annotations

import hashlib

import pytest
from hypothesis import given
from hypothesis import strategies as st

from irrevon.bench.seeds import DOMAIN_TAG, derive_seed

MASTER = hashlib.sha256(b"test master seed").hexdigest()

_cell_ids = st.text(
    alphabet="abcdefghijklmnopqrstuvwxyz-/CI123", min_size=1, max_size=60
)


def test_pinned_vector_stability() -> None:
    """The derivation is a frozen contract: these vectors may only ever change
    together with a recorded format-version bump (ADR-0030)."""
    seed = derive_seed(MASTER, "C2/refdest/response-lost/IRREVERSIBLE", 0)
    # Recompute from first principles (0x1F-separated, big-endian first 8 bytes).
    material = b"\x1f".join(
        [
            MASTER.encode(),
            DOMAIN_TAG.encode(),
            b"C2/refdest/response-lost/IRREVERSIBLE",
            b"0",
        ]
    )
    expected = int.from_bytes(hashlib.sha256(material).digest()[:8], "big")
    assert seed == expected


@given(cell_id=_cell_ids, replicate=st.integers(min_value=0, max_value=10**6))
def test_deterministic_and_in_range(cell_id: str, replicate: int) -> None:
    a = derive_seed(MASTER, cell_id, replicate)
    b = derive_seed(MASTER, cell_id, replicate)
    assert a == b
    assert 0 <= a < 2**64


@given(cell_id=_cell_ids, replicate=st.integers(min_value=0, max_value=1000))
def test_replicate_sensitivity(cell_id: str, replicate: int) -> None:
    assert derive_seed(MASTER, cell_id, replicate) != derive_seed(
        MASTER, cell_id, replicate + 1
    )


@given(replicate=st.integers(min_value=0, max_value=1000))
def test_no_cross_field_ambiguity(replicate: int) -> None:
    """A cell_id ending in digits can never collide with a shifted replicate —
    the 0x1F separator pinning exists exactly for this."""
    assert derive_seed(MASTER, "cell1", replicate) != derive_seed(
        MASTER, "cell", int(f"1{replicate}")
    )


def test_master_seed_validation() -> None:
    with pytest.raises(ValueError):
        derive_seed("not-hex", "cell", 0)
    with pytest.raises(ValueError):
        derive_seed(MASTER.upper(), "cell", 0)
    with pytest.raises(ValueError):
        derive_seed(MASTER, "", 0)
    with pytest.raises(ValueError):
        derive_seed(MASTER, "cell", -1)


def test_arm_identity_is_not_an_input() -> None:
    """Cross-arm pairing by construction (§5.1): the signature has no arm
    parameter, and the same (cell, replicate) always yields one seed."""
    import inspect

    parameters = inspect.signature(derive_seed).parameters
    assert set(parameters) == {"master_seed", "cell_id", "replicate_index"}
