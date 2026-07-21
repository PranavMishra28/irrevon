"""Deterministic race interleavings via sync points (testing.md §5) — no sleeps.

Covers the dispatch-vs-reconcile and sweep-vs-dispatch races (RFC-002 §13) with
one actor pinned at a named seam while the other proceeds. The same-stable-ids
races live in tests/integration/test_concurrency.py.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import psycopg
import pytest
from psycopg.rows import dict_row

from detent.adapters.base import declarations_dir, load_declaration
from detent.adapters.refdest import RefdestAdapter
from detent.dispatcher import dispatch
from detent.ledger import Ledger
from detent.reconciler import ReconcileConfig, reconcile_effect
from detent.sweep import sweep
from tests.integration.conftest import DBHandles
from tests.process.conftest import RefdestControl, contract

pytestmark = pytest.mark.integration

CONFIG = ReconcileConfig(stuck_threshold_s=300.0, absence_reread_gap_s=0.0)


def _adapter(base_url: str) -> RefdestAdapter:
    declaration = load_declaration(declarations_dir() / "refdest-c2.capability.json")
    return RefdestAdapter("refdest-c2", declaration, base_url=base_url)


def _sql(dsn: str, query: str, params: tuple[Any, ...] = ()) -> list[dict[str, Any]]:
    with psycopg.connect(dsn, row_factory=dict_row) as conn:
        return [dict(r) for r in conn.execute(query, params).fetchall()]  # type: ignore[arg-type]


def test_dispatch_racing_reconcile_denies_retry(
    fresh_db: DBHandles,
    refdest_server: tuple[str, RefdestControl],
    engine_factory: Any,
    tmp_path: Path,
) -> None:
    """§13 'dispatch racing reconcile': reconcile is paused between the
    destination status-query return and the settle; a concurrent agent retry
    must NOT re-dispatch — it sees pending_reconciliation (frontier AMBIGUOUS).
    Final state settles exactly once; destination count == 1."""
    base_url, control = refdest_server
    adapter = _adapter(base_url)

    # Setup (harness-side): response-lost dispatch → AMBIGUOUS.
    with Ledger(fresh_db.app_dsn) as ledger:
        raw = json.loads(contract("race-dvr"))
        reg = ledger.register_intent(raw, adapter.declaration_digest())
        control.schedule(
            [{"match": {"op": "create"}, "fault": "DROP_RESPONSE_AFTER_COMMIT"}]
        )
        report = dispatch(ledger, adapter, reg.effect_id)
        assert report.lifecycle == "AMBIGUOUS"

    # Engine process reconciles, pinned at reconcile.pre_settle (post-query).
    sync_dir = tmp_path / "sync"
    sync_dir.mkdir()
    engine = engine_factory(
        {"DETENT_SYNC_AT": "reconcile.pre_settle", "DETENT_SYNC_DIR": str(sync_dir)},
        wait_ready=False,
    )
    # Recovery itself reconciles this record — it hits the sync point.
    engine.wait_sentinel("HOOK reconcile.pre_settle REACHED")

    # The racing retry: dispatch must not fire a wire call.
    with Ledger(fresh_db.app_dsn) as ledger:
        racing = dispatch(ledger, adapter, reg.effect_id)
    assert racing.outcome == "pending_reconciliation"
    assert len(control.state()) == 1

    # Release the reconciler; it settles exactly once.
    (sync_dir / "reconcile.pre_settle.release").touch()
    engine.wait_sentinel("READY")
    rows = _sql(fresh_db.admin_dsn, "SELECT frontier FROM effect_frontiers")
    assert [r["frontier"] for r in rows] == ["SETTLED_COMMITTED"]
    findings = _sql(fresh_db.admin_dsn, "SELECT classification FROM findings")
    assert [f["classification"] for f in findings] == ["CONFIRMED_UNIQUE"]
    assert len(control.state()) == 1


def test_reconcile_racing_inflight_dispatch_classifies_nothing(
    fresh_db: DBHandles,
    refdest_server: tuple[str, RefdestControl],
    engine_factory: Any,
    tmp_path: Path,
) -> None:
    """Mirror case: dispatch pinned at adapter.pre_call (claim committed, wire
    not yet sent); online reconcile must observe the young in-flight attempt
    and classify NOTHING (no premature LOST finding)."""
    base_url, control = refdest_server
    adapter = _adapter(base_url)
    engine = engine_factory()
    reg = engine.send("REGISTER " + contract("race-rvd"))
    # The first engine holds the writer lock — close it BEFORE the pinned one
    # boots (the boot lock refuses a second engine).
    engine.close()

    sync_dir = tmp_path / "sync"
    sync_dir.mkdir()
    pinned = engine_factory(
        {"DETENT_SYNC_AT": "adapter.pre_call", "DETENT_SYNC_DIR": str(sync_dir)},
        wait_ready=False,
    )
    pinned.wait_sentinel("READY")
    pinned.send_nowait("DISPATCH " + reg["effect_id"])
    pinned.wait_sentinel("HOOK adapter.pre_call REACHED")

    # Online reconcile from the harness: the attempt is younger than the stuck
    # threshold — it must skip, not classify.
    with Ledger(fresh_db.app_dsn) as ledger:
        report = reconcile_effect(
            ledger, adapter, reg["effect_id"], mode="online", config=CONFIG
        )
    assert report.skipped_young, "a live wire call may still land (§6.1)"
    assert report.settled == []
    findings = _sql(fresh_db.admin_dsn, "SELECT 1 FROM findings")
    assert findings == []

    (sync_dir / "adapter.pre_call.release").touch()
    result = json.loads(
        pinned.wait_sentinel("RESULT ").removeprefix("RESULT ")
    )
    assert result["lifecycle"] == "SETTLED_COMMITTED"
    assert len(control.state()) == 1


def test_sweep_racing_dispatch_no_false_orphan(
    fresh_db: DBHandles,
    refdest_server: tuple[str, RefdestControl],
    engine_factory: Any,
    tmp_path: Path,
) -> None:
    """§13 'sweep racing dispatch': the destination effect exists, the receipt
    is not yet committed. The sweep's match order catches the stamped client
    reference (= operation_id, durably in effect_executions), so NO false
    ORPHANED finding — while genuinely out-of-band effects in the same window
    are still detected (the race fix must not blind the sweep)."""
    base_url, control = refdest_server
    adapter = _adapter(base_url)
    engine = engine_factory()
    reg = engine.send("REGISTER " + contract("race-svd"))
    engine.close()

    oob = control.oob_create("order.create", {"out_of_band": True})

    sync_dir = tmp_path / "sync"
    sync_dir.mkdir()
    pinned = engine_factory(
        {"DETENT_SYNC_AT": "adapter.post_call", "DETENT_SYNC_DIR": str(sync_dir)},
        wait_ready=False,
    )
    pinned.wait_sentinel("READY")
    pinned.send_nowait("DISPATCH " + reg["effect_id"])
    # Destination has the effect; the engine is frozen pre-receipt.
    pinned.wait_sentinel("HOOK adapter.post_call REACHED")
    assert len(control.state()) == 2  # in-flight + OOB

    with Ledger(fresh_db.app_dsn) as ledger:
        first = sweep(ledger, adapter, "2026-01-01", "2027-01-01")
        second = sweep(ledger, adapter, "2026-01-01", "2027-01-01")
    assert first.new_findings == []
    assert len(second.new_findings) == 1, "the OOB effect must still be caught"
    orphans = _sql(
        fresh_db.admin_dsn,
        "SELECT destination_ref FROM findings WHERE classification = 'ORPHANED'",
    )
    assert [o["destination_ref"] for o in orphans] == [oob["destination_ref"]]

    (sync_dir / "adapter.post_call.release").touch()
    result = json.loads(pinned.wait_sentinel("RESULT ").removeprefix("RESULT "))
    assert result["lifecycle"] == "SETTLED_COMMITTED"


def test_sweep_vs_killed_dispatcher_single_finding(
    fresh_db: DBHandles,
    refdest_server: tuple[str, RefdestControl],
    engine_factory: Any,
) -> None:
    """Adversarial variant: SIGKILL the dispatcher at receipt.pre_commit
    (destination has the effect; ledger has no receipt), sweep twice, then
    recover. The effect must surface as the record's reconciliation
    (CONFIRMED_UNIQUE), never as an orphan — exactly ONE finding across the
    two detection paths."""
    base_url, control = refdest_server
    adapter = _adapter(base_url)
    engine = engine_factory()
    reg = engine.send("REGISTER " + contract("race-svk"))
    engine.close()

    armed = engine_factory({"DETENT_CRASH_AT": "receipt.pre_commit"})
    armed.send_nowait("DISPATCH " + reg["effect_id"])
    armed.assert_died_by_sigkill()
    assert len(control.state()) == 1

    with Ledger(fresh_db.app_dsn) as ledger:
        sweep(ledger, adapter, "2026-01-01", "2027-01-01")
        report = sweep(ledger, adapter, "2026-01-01", "2027-01-01")
    assert report.new_findings == [], "an in-flight dispatch is never an orphan"

    engine_factory()  # recovery adjudicates
    findings = _sql(
        fresh_db.admin_dsn, "SELECT classification, effect_id FROM findings"
    )
    assert len(findings) == 1, "exactly one finding across both detection paths"
    assert findings[0]["classification"] == "CONFIRMED_UNIQUE"
    assert findings[0]["effect_id"] == reg["effect_id"]
