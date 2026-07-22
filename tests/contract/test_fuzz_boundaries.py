"""Fuzz harnesses for the parser trust boundaries (security-policy §supply-chain).

Hypothesis-as-fuzzer (the low-noise 2026 Python practice): these run in the
normal pytest tiers at the CI example budgets and double as Atheris-style
harnesses locally. Two boundaries:

1. Intent-contract validation — arbitrary JSON-shaped input must yield
   ``ContractInvalid`` or a fully validated contract; never any other
   exception, never a contract whose identity members escaped validation.
2. JCS canonicalization — differential against a stdlib re-encoding on the
   JSON-safe subset (sorted keys, compact, ensure_ascii=False matches RFC
   8785 for this subset); non-representable inputs raise the encoder's
   documented errors only.
"""

from __future__ import annotations

import json

from hypothesis import given
from hypothesis import strategies as st

from irrevon.contract import validate_intent_contract
from irrevon.contract.validation import IntentContract
from irrevon.errors import ContractInvalid
from irrevon.identity import canonical_bytes

# JSON-safe scalars: strings, bools, None, and integers inside the JCS
# (I-JSON) safe range. Floats are excluded from the differential leg because
# JCS number serialization (ECMA-262) legitimately differs from json.dumps.
_scalars = st.one_of(
    st.text(max_size=40),
    st.booleans(),
    st.none(),
    st.integers(min_value=-(2**53) + 1, max_value=2**53 - 1),
)
# Differential-leg OBJECT KEYS are BMP-only: RFC 8785 §3.2.3 sorts keys by
# UTF-16 code units, which diverges from Python's code-point sort exactly when
# a non-BMP key (surrogate-pair lead 0xD800–0xDBFF) meets a BMP key in
# U+E000–U+FFFF. This fuzz suite FOUND that divergence on its first CI-budget
# run; the conformance pin below keeps it found forever.
_bmp_keys = st.text(
    alphabet=st.characters(max_codepoint=0xFFFF, exclude_categories=("Cs",)),
    max_size=20,
)
_json_safe = st.recursive(
    _scalars,
    lambda children: st.one_of(
        st.lists(children, max_size=6),
        st.dictionaries(_bmp_keys, children, max_size=6),
    ),
    max_leaves=25,
)

_arbitrary_json = st.recursive(
    st.one_of(_scalars, st.floats(allow_nan=False, allow_infinity=False)),
    lambda children: st.one_of(
        st.lists(children, max_size=6),
        st.dictionaries(st.text(max_size=20), children, max_size=6),
    ),
    max_leaves=25,
)


@given(raw=_arbitrary_json)
def test_contract_validation_never_crashes_or_bypasses(raw: object) -> None:
    """Boundary 1: any input → ContractInvalid or a validated contract."""
    try:
        contract = validate_intent_contract(raw)
    except ContractInvalid:
        return
    # If it validated, the identity members are typed and non-empty — the
    # trust boundary held (no partially-validated object can escape).
    assert isinstance(contract, IntentContract)
    assert contract.stable_ids and all(
        type(k) is str and type(v) is str for k, v in contract.stable_ids.items()
    )
    assert type(contract.effect_type) is str and contract.effect_type
    assert type(contract.scope) is str and contract.scope


@given(payload=st.dictionaries(st.text(min_size=1, max_size=20), _arbitrary_json, max_size=8))
def test_contract_parameters_never_reach_identity(payload: dict[str, object]) -> None:
    """Fuzzing the NON-identity payload while the identity tuple is fixed must
    never change the validated identity members (master doc §12.1 row 1)."""
    raw = {
        "schema_version": "1",
        "stable_ids": {"order_id": "77"},
        "effect_type": "order.create",
        "effect_class": "IRREVERSIBLE",
        "scope": "fuzz/77",
        "adapter_id": "refdest-c2",
        "parameters": payload,
        "authority_ref": "auth_fuzz",
        "stamped_at": "2026-07-22T00:00:00Z",
    }
    try:
        contract = validate_intent_contract(raw)
    except ContractInvalid:
        return  # schema may reject exotic payload shapes; that is a valid outcome
    assert contract.stable_ids == {"order_id": "77"}
    assert contract.effect_type == "order.create"
    assert contract.scope == "fuzz/77"


@given(value=_json_safe)
def test_jcs_differential_on_the_safe_subset(value: object) -> None:
    """Boundary 2: on the JSON-safe, BMP-keyed subset, the pinned rfc8785
    encoder must agree byte-for-byte with the stdlib canonical re-encoding
    (the equivalence the stdlib bench-integrity gate relies on — its fixture
    universe is ASCII-keyed, well inside this subset)."""
    ours = canonical_bytes(value)
    stdlib = json.dumps(
        value, sort_keys=True, separators=(",", ":"), ensure_ascii=False
    ).encode("utf-8")
    assert ours == stdlib
    # And canonicalization is a fixpoint: decode → re-encode is stable.
    assert canonical_bytes(json.loads(ours)) == ours


def test_jcs_utf16_key_ordering_conformance_pin() -> None:
    """RFC 8785 §3.2.3 conformance: keys sort by UTF-16 CODE UNITS. '𐀀'
    (U+10000, surrogate pair D800 DC00) must sort BEFORE '\ue000' (E000)
    although its code point is higher — the divergence this suite's first
    fuzz run discovered. The stdlib approximation gets this wrong, which is
    exactly why the stdlib bench-integrity gate documents an ASCII-key
    fixture universe and the encoder-exact parity lives here."""
    ours = canonical_bytes({"\U00010000": 1, "\ue000": 2})
    assert ours == '{"\U00010000":1,"\ue000":2}'.encode()
    stdlib = json.dumps(
        {"\U00010000": 1, "\ue000": 2}, sort_keys=True,
        separators=(",", ":"), ensure_ascii=False,
    ).encode("utf-8")
    assert ours != stdlib  # the documented boundary, pinned in both directions
