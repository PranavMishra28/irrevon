"""Capability conformance: matched stacks conform; drifted stacks are caught.

Differential design: the SAME prober runs against correctly-declared and
deliberately mis-declared adapter/destination pairs — the mis-declared pairs
MUST produce mismatches (a conformance verifier that can't catch drift is
worse than none)."""

from __future__ import annotations

import pytest

from irrevon.adapters.base import declarations_dir, load_declaration
from irrevon.adapters.refdest import RefDest, RefdestAdapter
from irrevon.bench.conformance import verify_declaration


def _adapter(declared_tier: str, destination_tier: str, **quirks: bool) -> RefdestAdapter:
    declaration = load_declaration(
        declarations_dir() / f"refdest-{declared_tier.lower()}.capability.json"
    )
    refdest = RefDest(seed=11, profile=destination_tier, **quirks)
    return RefdestAdapter(f"refdest-{declared_tier.lower()}", declaration, instance=refdest)


@pytest.mark.parametrize("tier", ["C1", "C2", "C3"])
def test_matched_declarations_are_conformant(tier: str) -> None:
    report = verify_declaration(_adapter(tier, tier))
    assert report["verdict"] == "conformant", report["probes"]
    assert report["format"] == "irrevonbench/conformance/v1"
    assert report["declaration_digest"].startswith("sha256:")


def test_c1_declaration_on_c2_destination_catches_ignored_keys() -> None:
    """The core drift case: declared idempotency, destination silently ignores
    the key — exactly the C2 wedge, observed empirically."""
    report = verify_declaration(_adapter("C1", "C2"))
    assert report["verdict"] == "non-conformant"
    idem = next(p for p in report["probes"] if p["capability"] == "idempotency.supported")
    assert idem["verdict"] == "mismatch"
    assert idem["declared"] is True and idem["observed"] is False


def test_c2_declaration_on_c3_destination_catches_missing_query() -> None:
    report = verify_declaration(_adapter("C2", "C3"))
    assert report["verdict"] == "non-conformant"
    query = next(p for p in report["probes"] if p["capability"] == "queryable.client_ref")
    assert query["verdict"] == "mismatch"


def test_denied_capabilities_report_unverifiable_never_match() -> None:
    """Honest verification boundary: a capability the declaration denies (and
    the adapter therefore never exercises) is 'unverifiable' — the verifier
    must not launder it into a 'match'."""
    report = verify_declaration(_adapter("C2", "C2"))
    idem = next(p for p in report["probes"] if p["capability"] == "idempotency.supported")
    assert idem["verdict"] == "unverifiable"


def test_matched_c2_probes_cover_query_absence_and_listing() -> None:
    report = verify_declaration(_adapter("C2", "C2"))
    capabilities = {p["capability"]: p["verdict"] for p in report["probes"]}
    assert capabilities["queryable.client_ref"] == "match"
    assert capabilities["queryable.destination_ref"] == "match"
    assert capabilities["queryable.authoritative_absence"] == "match"
    assert capabilities["list_queryable.enumeration_complete"] == "match"


def test_conformance_survives_enrichment_quirk() -> None:
    """Destination-side normalization must not break conformance probing (the
    probes use references, never payload byte-identity)."""
    report = verify_declaration(_adapter("C2", "C2", enrichment_quirk=True))
    assert report["verdict"] == "conformant", report["probes"]
