"""The continuous worker service (ADR-0034 proposed): reconcile scheduling,
sweeps, gauges, health freshness, single-writer exclusion, graceful shutdown."""

from __future__ import annotations

import json
import os
import signal
import threading
import time
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

import pytest

from irrevon.adapters.base import declarations_dir, load_declaration
from irrevon.adapters.refdest import RefDest, RefdestAdapter
from irrevon.api import Engine
from irrevon.dispatcher import dispatch
from irrevon.errors import StorageUnavailable
from irrevon.ledger import Ledger
from irrevon.worker import WorkerConfig, run_worker
from tests.integration.conftest import DBHandles

pytestmark = pytest.mark.integration

C2_DECL = load_declaration(declarations_dir() / "refdest-c2.capability.json")


def _c2() -> tuple[RefDest, RefdestAdapter]:
    refdest = RefDest(seed=11, profile="C2")
    return refdest, RefdestAdapter("refdest-c2", C2_DECL, instance=refdest)


def _raw(order_id: str) -> dict[str, Any]:
    return {
        "schema_version": "1",
        "stable_ids": {"order_id": order_id},
        "effect_type": "order.create",
        "effect_class": "IRREVERSIBLE",
        "scope": f"worker/{order_id}",
        "adapter_id": "refdest-c2",
        "parameters": {"note": "worker-test"},
        "authority_ref": "auth_worker",
        "stamped_at": datetime.now(UTC).isoformat().replace("+00:00", "Z"),
    }


def _ambiguous_effect(dsn: str, refdest: RefDest, adapter: RefdestAdapter, oid: str) -> str:
    with Ledger(dsn) as ledger:
        reg = ledger.register_intent(_raw(oid), adapter.declaration_digest())
        refdest.control_schedule(
            [{"match": {"op": "create"}, "fault": "DROP_RESPONSE_AFTER_COMMIT"}]
        )
        report = dispatch(ledger, adapter, reg.effect_id)
        assert report.lifecycle == "AMBIGUOUS"
        return reg.effect_id


def test_worker_settles_open_work_and_reports_health(
    fresh_db: DBHandles, tmp_path: Path
) -> None:
    refdest, adapter = _c2()
    effect_id = _ambiguous_effect(fresh_db.app_dsn, refdest, adapter, "wk-1")
    health = tmp_path / "health.json"
    code = run_worker(
        fresh_db.app_dsn,
        {"refdest-c2": adapter},
        WorkerConfig(
            reconcile_interval_s=0.05,
            sweep_interval_s=0.05,
            health_file=health,
            max_cycles=3,
        ),
    )
    assert code == 0
    with Ledger(fresh_db.app_dsn) as ledger:
        assert ledger.effect_frontier(effect_id)["frontier"] == "SETTLED_COMMITTED"
        classifications = [f["classification"] for f in ledger.findings_for(effect_id)]
        assert classifications == ["CONFIRMED_UNIQUE"]
        # The sweep interval elapsed at least once → a sweep run was journaled.
        sweeps = ledger.query("SELECT run_id FROM sweep_runs")
        assert sweeps
    payload = json.loads(health.read_text(encoding="utf-8"))
    assert payload["cycle"] == 3
    assert payload["open_executions"] == 0
    assert payload["open_findings"] == 0  # CONFIRMED_UNIQUE auto-closes


def test_second_worker_is_refused_by_the_writer_lock(fresh_db: DBHandles) -> None:
    """Single-writer invariant holds for the service exactly as for the boot
    path (ADR-002): a second worker refuses to start, never splits the brain."""
    _refdest, adapter = _c2()
    holder = Engine(fresh_db.app_dsn, {"refdest-c2": adapter})
    holder.boot()
    try:
        with pytest.raises(StorageUnavailable, match="single-writer"):
            run_worker(
                fresh_db.app_dsn,
                {"refdest-c2": adapter},
                WorkerConfig(reconcile_interval_s=0.05, max_cycles=1),
            )
    finally:
        holder.close()


def test_worker_sigterm_stops_gracefully(fresh_db: DBHandles, tmp_path: Path) -> None:
    """SIGTERM mid-run: the loop finishes its cycle, closes the engine, and
    returns 0 — no new work is claimed after the signal."""
    refdest, adapter = _c2()
    _ambiguous_effect(fresh_db.app_dsn, refdest, adapter, "wk-term")

    def _send_sigterm_soon() -> None:
        time.sleep(0.4)
        os.kill(os.getpid(), signal.SIGTERM)

    thread = threading.Thread(target=_send_sigterm_soon, daemon=True)
    thread.start()
    code = run_worker(
        fresh_db.app_dsn,
        {"refdest-c2": adapter},
        WorkerConfig(
            reconcile_interval_s=0.1,
            sweep_interval_s=60.0,
            health_file=tmp_path / "health.json",
            max_cycles=None,  # would run forever without the signal
        ),
    )
    thread.join(timeout=5)
    assert code == 0
    # The writer lock was released: a fresh engine can boot immediately.
    follow_up = Engine(fresh_db.app_dsn, {"refdest-c2": adapter})
    follow_up.boot()
    follow_up.close()
