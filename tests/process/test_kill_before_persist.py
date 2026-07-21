"""Kill-before-persist and the crash-point seam catalog (testing.md §4.2/§6).

Conformance: master doc §12.1 row 2 — "No dispatch without a durably persisted
intent (§7.4)" (M3). The engine is a REAL subprocess SIGKILLed at armed seams;
the oracle is the refdest truth API plus direct SQL — never the engine. Zero
destination effects without a durable PERSISTED record; ZERO tolerance, no
flaky-retry policy: a single violation is a real bug by construction.
"""

from __future__ import annotations

from typing import Any

import psycopg
import pytest
from psycopg.rows import dict_row

from tests.integration.conftest import DBHandles
from tests.process.conftest import RefdestControl, contract

pytestmark = pytest.mark.integration


def _sql(dsn: str, query: str, params: tuple[Any, ...] = ()) -> list[dict[str, Any]]:
    with psycopg.connect(dsn, row_factory=dict_row) as conn:
        return [dict(r) for r in conn.execute(query, params).fetchall()]  # type: ignore[arg-type]


def test_kill_at_persist_pre_commit_is_effect_free(
    fresh_db: DBHandles,
    refdest_server: tuple[str, RefdestControl],
    engine_factory: Any,
) -> None:
    """Killed at/before persist COMMIT: destination effect count == 0 AND the
    ledger has no record — crash-before-persist is provably effect-free."""
    _, control = refdest_server
    engine = engine_factory({"IRREVON_CRASH_AT": "persist.pre_commit"})
    engine.send_nowait("REGISTER " + contract("kbp-1"))
    engine.assert_died_by_sigkill()

    assert control.state() == [], "no destination effect may exist"
    assert _sql(fresh_db.admin_dsn, "SELECT 1 FROM effect_records") == []
    assert _sql(fresh_db.admin_dsn, "SELECT 1 FROM effect_transitions") == []


def test_kill_at_persist_post_commit_leaves_durable_persisted(
    fresh_db: DBHandles,
    refdest_server: tuple[str, RefdestControl],
    engine_factory: Any,
) -> None:
    _, control = refdest_server
    engine = engine_factory({"IRREVON_CRASH_AT": "persist.post_commit"})
    engine.send_nowait("REGISTER " + contract("kbp-2"))
    engine.assert_died_by_sigkill()

    assert control.state() == []
    rows = _sql(fresh_db.admin_dsn, "SELECT frontier FROM effect_frontiers")
    assert [r["frontier"] for r in rows] == ["PERSISTED"]


@pytest.mark.parametrize("seam", ["gate.post_allow", "adapter.pre_call"])
def test_kill_after_claim_before_wire(
    seam: str,
    fresh_db: DBHandles,
    refdest_server: tuple[str, RefdestControl],
    engine_factory: Any,
) -> None:
    """Killed after the claim commit but before any bytes leave the process:
    destination count == 0; the durable open attempt exists (DISPATCHED); and
    post-restart recovery adjudicates BEFORE any new dispatch."""
    _, control = refdest_server
    setup = engine_factory()
    reg = setup.send("REGISTER " + contract(f"kbp-{seam}"))
    setup.close()

    armed = engine_factory({"IRREVON_CRASH_AT": seam})
    armed.send_nowait("DISPATCH " + reg["effect_id"])
    armed.assert_died_by_sigkill()

    assert control.state() == [], "no wire call may have started"
    rows = _sql(fresh_db.admin_dsn, "SELECT frontier FROM effect_frontiers")
    assert [r["frontier"] for r in rows] == ["DISPATCHED"]
    assert _sql(fresh_db.admin_dsn, "SELECT 1 FROM open_attempts") != []

    # Restart: recovery must adjudicate before accepting work — the request
    # log proves order: the status query precedes any (absent) re-dispatch.
    creates_before = [r for r in control.log() if r["op"] == "create"]
    engine_factory()  # spawn waits for READY, i.e. recovery completed
    rows = _sql(fresh_db.admin_dsn, "SELECT frontier FROM effect_frontiers")
    # Confirmed absent (two reads, PT0S lag) → SETTLED_FAILED + LOST(OPEN).
    assert [r["frontier"] for r in rows] == ["SETTLED_FAILED"]
    findings = _sql(fresh_db.admin_dsn, "SELECT classification FROM findings")
    assert [f["classification"] for f in findings] == ["LOST"]
    creates_after = [r for r in control.log() if r["op"] == "create"]
    assert creates_before == creates_after, "recovery must not re-dispatch on belief"
    queries = [r for r in control.log() if r["op"] == "query"]
    assert len(queries) >= 2, "confirmed absence requires two reads"


def test_kill_between_destination_effect_and_receipt(
    fresh_db: DBHandles,
    refdest_server: tuple[str, RefdestControl],
    engine_factory: Any,
) -> None:
    """Crash-after-effect-before-response (RFC-001 §9.5 fault 2): the effect
    exists at the destination; the receipt was never recorded. Recovery must
    reconcile-by-query to SETTLED_COMMITTED + CONFIRMED_UNIQUE — never
    re-dispatch (destination count stays 1)."""
    _, control = refdest_server
    setup = engine_factory()
    reg = setup.send("REGISTER " + contract("kbp-effect-no-receipt"))
    setup.close()

    armed = engine_factory({"IRREVON_CRASH_AT": "receipt.pre_commit"})
    armed.send_nowait("DISPATCH " + reg["effect_id"])
    armed.assert_died_by_sigkill()

    assert len(control.state()) == 1, "the destination effect was committed"
    rows = _sql(fresh_db.admin_dsn, "SELECT frontier FROM effect_frontiers")
    assert [r["frontier"] for r in rows] == ["DISPATCHED"]

    recovered = engine_factory()
    _ = recovered
    rows = _sql(fresh_db.admin_dsn, "SELECT frontier FROM effect_frontiers")
    assert [r["frontier"] for r in rows] == ["SETTLED_COMMITTED"]
    findings = _sql(
        fresh_db.admin_dsn, "SELECT classification, effect_id FROM findings"
    )
    assert [f["classification"] for f in findings] == ["CONFIRMED_UNIQUE"]
    assert len(control.state()) == 1, "recovery must not create a second effect"


def test_kill_after_receipt_commit_is_stable(
    fresh_db: DBHandles,
    refdest_server: tuple[str, RefdestControl],
    engine_factory: Any,
) -> None:
    _, control = refdest_server
    setup = engine_factory()
    reg = setup.send("REGISTER " + contract("kbp-post-receipt"))
    setup.close()

    armed = engine_factory({"IRREVON_CRASH_AT": "receipt.post_commit"})
    armed.send_nowait("DISPATCH " + reg["effect_id"])
    armed.assert_died_by_sigkill()

    assert len(control.state()) == 1
    rows = _sql(fresh_db.admin_dsn, "SELECT frontier FROM effect_frontiers")
    assert [r["frontier"] for r in rows] == ["SETTLED_COMMITTED"]

    # Restart is a no-op: nothing open, nothing re-dispatched.
    recovered = engine_factory()
    _ = recovered
    assert len(control.state()) == 1


def test_zero_effects_without_persisted_record_across_all_seams(
    fresh_db: DBHandles,
    refdest_server: tuple[str, RefdestControl],
    engine_factory: Any,
) -> None:
    """The row-2 binding claim, asserted globally: every destination effect
    maps to a ledger record that reached DISPATCHED (zero tolerance)."""
    _, control = refdest_server

    # Seam 1: register dies pre-commit — nothing anywhere.
    armed = engine_factory({"IRREVON_CRASH_AT": "persist.pre_commit"})
    armed.send_nowait("REGISTER " + contract("kbp-sweep-0"))
    armed.assert_died_by_sigkill()

    # Seams 2-3: dispatch dies before/after the wire call.
    for i, seam in enumerate(["gate.post_allow", "receipt.pre_commit"], start=1):
        setup = engine_factory()
        reg = setup.send("REGISTER " + contract(f"kbp-sweep-{i}"))
        setup.close()
        armed = engine_factory({"IRREVON_CRASH_AT": seam})
        armed.send_nowait("DISPATCH " + reg["effect_id"])
        armed.assert_died_by_sigkill()

    dispatched_ops = {
        r["operation_id"]
        for r in _sql(
            fresh_db.admin_dsn,
            "SELECT DISTINCT e.operation_id FROM effect_transitions t "
            "JOIN effect_executions e USING (execution_id) "
            "WHERE t.to_state = 'DISPATCHED'",
        )
    }
    for effect in control.state():
        assert effect["client_ref"] in dispatched_ops, (
            f"destination effect {effect['destination_ref']} exists without a "
            "durable DISPATCHED record — kill-before-persist violated"
        )
