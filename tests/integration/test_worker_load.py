"""Bounded load/soak evidence for the worker loop (docs/operations.md).

Not a performance CLAIM — an executed regression bound: the single-writer
loop must drain a realistic backlog (60 ambiguous effects across distinct
scopes) within a generous budget, settle every one correctly, keep the
auditor clean (the fresh_db fixture re-audits on teardown), and leave no
open findings. Numbers land in the test output, never in any product claim."""

from __future__ import annotations

import time
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

import pytest

from irrevon.adapters.base import declarations_dir, load_declaration
from irrevon.adapters.refdest import RefDest, RefdestAdapter
from irrevon.dispatcher import dispatch
from irrevon.ledger import Ledger
from irrevon.worker import WorkerConfig, run_worker
from tests.integration.conftest import DBHandles

pytestmark = pytest.mark.integration

C2_DECL = load_declaration(declarations_dir() / "refdest-c2.capability.json")
BACKLOG = 60


def _raw(i: int) -> dict[str, Any]:
    return {
        "schema_version": "1",
        "stable_ids": {"order_id": f"load-{i}"},
        "effect_type": "order.create",
        "effect_class": "IRREVERSIBLE",
        "scope": f"load/{i}",
        "adapter_id": "refdest-c2",
        "parameters": {"n": i},
        "authority_ref": "auth_load",
        "stamped_at": datetime.now(UTC).isoformat().replace("+00:00", "Z"),
    }


def test_worker_drains_a_backlog_within_budget(
    fresh_db: DBHandles, tmp_path: Path
) -> None:
    refdest = RefDest(seed=31, profile="C2")
    adapter = RefdestAdapter("refdest-c2", C2_DECL, instance=refdest)
    with Ledger(fresh_db.app_dsn) as ledger:
        for i in range(BACKLOG):
            reg = ledger.register_intent(_raw(i), adapter.declaration_digest())
            refdest.control_schedule(
                [{"match": {"op": "create"}, "fault": "DROP_RESPONSE_AFTER_COMMIT"}]
            )
            report = dispatch(ledger, adapter, reg.effect_id)
            assert report.lifecycle == "AMBIGUOUS"

    started = time.monotonic()
    code = run_worker(
        fresh_db.app_dsn,
        {"refdest-c2": adapter},
        WorkerConfig(
            reconcile_interval_s=0.05,
            sweep_interval_s=3600.0,  # sweeps out of the way; this measures drain
            health_file=tmp_path / "health.json",
            max_cycles=4,
        ),
    )
    elapsed = time.monotonic() - started
    assert code == 0
    with Ledger(fresh_db.app_dsn) as ledger:
        rows = ledger.query(
            "SELECT frontier, count(*) AS n FROM execution_frontiers GROUP BY frontier"
        )
        by_frontier = {r["frontier"]: int(r["n"]) for r in rows}
        assert by_frontier == {"SETTLED_COMMITTED": BACKLOG}
        open_findings = ledger.query(
            """
            SELECT count(*) AS n FROM findings f
            WHERE NOT EXISTS (SELECT 1 FROM finding_resolutions r
                              WHERE r.finding_id = f.finding_id AND r.to_status = 'CLOSED')
            """
        )
        assert int(open_findings[0]["n"]) == 0
        # Exactly one destination effect per intent (no reconcile-path dups).
        assert len(refdest.control_state()) == BACKLOG
    # Generous regression budget: a drain this size taking minutes would mean
    # a pathological regression (each settle = one probe + one transition).
    assert elapsed < 60, f"backlog drain took {elapsed:.1f}s for {BACKLOG} effects"
    print(f"\nworker drain evidence: {BACKLOG} ambiguous effects settled in {elapsed:.2f}s")
