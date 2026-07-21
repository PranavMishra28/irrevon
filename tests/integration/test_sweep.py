"""Orphan sweep (RFC-002 §7.2).

Conformance: master doc §12.1 row 7 — "Orphans representable without a ledger
record (§7.1)" (brought forward to the refdest per the T-103 scope): K
out-of-band effects yield exactly K ORPHANED findings keyed by
(adapter_id, destination_ref); zero false orphans for ledgered dispatches; no
EffectRecord row is created for an orphan.
"""

from __future__ import annotations

from datetime import UTC, datetime
from typing import Any

import pytest

from detent.adapters.base import declarations_dir, load_declaration
from detent.adapters.refdest import RefDest, RefdestAdapter
from detent.dispatcher import dispatch
from detent.ledger import Ledger
from detent.sweep import sweep
from tests.integration.conftest import DBHandles

pytestmark = pytest.mark.integration

C2_DECL = load_declaration(declarations_dir() / "refdest-c2.capability.json")


def _raw(order_id: str) -> dict[str, Any]:
    return {
        "schema_version": "1",
        "stable_ids": {"order_id": order_id},
        "effect_type": "order.create",
        "effect_class": "IRREVERSIBLE",
        "scope": f"sweep/{order_id}",
        "adapter_id": "refdest-c2",
        "parameters": {},
        "authority_ref": "auth_sw",
        "stamped_at": datetime.now(UTC).isoformat().replace("+00:00", "Z"),
    }


def test_k_oob_effects_yield_exactly_k_orphans(fresh_db: DBHandles) -> None:
    refdest = RefDest(seed=11)
    adapter = RefdestAdapter("refdest-c2", C2_DECL, instance=refdest)
    with Ledger(fresh_db.app_dsn) as ledger:
        # J = 2 legitimate dispatches through Detent in the same window.
        for i in range(2):
            reg = ledger.register_intent(_raw(f"sw-legit-{i}"), adapter.declaration_digest())
            report = dispatch(ledger, adapter, reg.effect_id)
            assert report.lifecycle == "SETTLED_COMMITTED"
        # K = 3 out-of-band effects bypassing Detent entirely.
        oob_refs = {
            refdest.control_oob_create("order.create", {"oob": i})["destination_ref"]
            for i in range(3)
        }

        records_before = ledger.query("SELECT count(*) AS n FROM effect_records")

        first = sweep(ledger, adapter, "2026-01-01", "2027-01-01")
        assert first.listed == 5
        assert first.matched == 2
        assert first.new_findings == [], "one sighting is never enough (two-run rule)"

        second = sweep(ledger, adapter, "2026-01-01", "2027-01-01")
        assert len(second.new_findings) == 3, "exactly K ORPHANED findings"

        orphans = ledger.query(
            "SELECT effect_id, adapter_id, destination_ref, evidence FROM findings "
            "WHERE classification = 'ORPHANED' ORDER BY finding_id"
        )
        assert {o["destination_ref"] for o in orphans} == oob_refs
        assert all(o["effect_id"] is None for o in orphans), (
            "ORPHANED is keyed by (adapter, destination_ref), never a record"
        )
        assert all(o["adapter_id"] == "refdest-c2" for o in orphans)
        assert all(o["evidence"]["payload_digest"].startswith("sha256:") for o in orphans)

        # No EffectRecord row was created for any orphan (RFC-001 §2 rule).
        records_after = ledger.query("SELECT count(*) AS n FROM effect_records")
        assert records_after[0]["n"] == records_before[0]["n"]

        # Idempotence: a third overlapping sweep emits no duplicate findings.
        third = sweep(ledger, adapter, "2026-01-01", "2027-01-01")
        assert third.new_findings == []
        count = ledger.query(
            "SELECT count(*) AS n FROM findings WHERE classification = 'ORPHANED'"
        )
        assert count[0]["n"] == 3


def test_sweep_outside_window_finds_nothing(fresh_db: DBHandles) -> None:
    refdest = RefDest(seed=11)
    adapter = RefdestAdapter("refdest-c2", C2_DECL, instance=refdest)
    with Ledger(fresh_db.app_dsn) as ledger:
        refdest.control_oob_create("order.create", {"oob": True})
        report = sweep(ledger, adapter, "2030-01-01", "2031-01-01")
        assert report.listed == 0
        assert report.new_findings == []


def test_sweep_compensates_default_filter_quirk(fresh_db: DBHandles) -> None:
    """The declared default-filter quirk (à la EasyPost purchased=true) must
    not blind the sweep: the adapter lists with the override."""
    refdest = RefDest(seed=11, default_filter_quirk=True)
    adapter = RefdestAdapter("refdest-c2", C2_DECL, instance=refdest)
    with Ledger(fresh_db.app_dsn) as ledger:
        hidden = refdest.control_oob_create("order.create", {"hidden": True})
        # The quirk hides it from a default listing…
        status, body, _ = refdest.api_list("2026-01-01", "2027-01-01")
        assert status == 200 and body["effects"] == []
        # …but not from the sweep.
        sweep(ledger, adapter, "2026-01-01", "2027-01-01")
        second = sweep(ledger, adapter, "2026-01-01", "2027-01-01")
        assert len(second.new_findings) == 1
        orphan = ledger.query(
            "SELECT destination_ref FROM findings WHERE classification = 'ORPHANED'"
        )
        assert orphan[0]["destination_ref"] == hidden["destination_ref"]
