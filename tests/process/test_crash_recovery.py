"""Crash-recovery replay (RFC-002 §7.1; testing.md §6).

Restart adjudicates every DISPATCHED/AMBIGUOUS record BEFORE any new dispatch
(the refdest request-log order proves it); recovery is re-entrant under
mid-recovery kills; a second engine process is refused by the writer lock.
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


def test_response_lost_crash_restart_reconciles_without_redispatch(
    fresh_db: DBHandles,
    refdest_server: tuple[str, RefdestControl],
    engine_factory: Any,
) -> None:
    """The flagship fault-1 shape: dispatch, response lost on cue, SIGKILL,
    restart → replay reconciles to SETTLED_COMMITTED + CONFIRMED_UNIQUE; the
    destination request log shows status-query BEFORE any dispatch and no new
    create at all; destination effect count == 1."""
    _, control = refdest_server
    control.schedule(
        [{"match": {"op": "create"}, "fault": "DROP_RESPONSE_AFTER_COMMIT"}]
    )
    engine = engine_factory()
    reg = engine.send("REGISTER " + contract("cr-flagship"))
    result = engine.send("DISPATCH " + reg["effect_id"])
    assert result["lifecycle"] == "AMBIGUOUS"
    assert result["transport_outcome"] == "LOST"
    assert len(control.state()) == 1, "the effect was committed server-side"

    engine.sigkill()
    engine.assert_died_by_sigkill()
    log_before = control.log()

    recovered = engine_factory()
    recovery_line = [s for s in recovered.sentinels if s.startswith("RECOVERY DONE")]
    assert recovery_line, "recovery sentinel must precede READY"

    rows = _sql(fresh_db.admin_dsn, "SELECT frontier FROM effect_frontiers")
    assert [r["frontier"] for r in rows] == ["SETTLED_COMMITTED"]
    findings = _sql(fresh_db.admin_dsn, "SELECT classification FROM findings")
    assert [f["classification"] for f in findings] == ["CONFIRMED_UNIQUE"]
    assert len(control.state()) == 1, "no re-dispatch may have happened"

    log_after = control.log()
    new_ops = [r["op"] for r in log_after[len(log_before):]]
    assert "create" not in new_ops, "adjudicate-before-redispatch violated"
    assert "query" in new_ops, "recovery must have queried the destination"


def test_recovery_is_reentrant_under_mid_recovery_kills(
    fresh_db: DBHandles,
    refdest_server: tuple[str, RefdestControl],
    engine_factory: Any,
) -> None:
    """Seed 3 in-doubt records (distinct scopes) with a truth split: two
    present at the destination, one absent. Kill recovery after the first
    record, restart, kill after the second, restart, complete. All records
    settle per the fixture truth; destination counts unchanged by the number
    of crashes; no duplicate findings (auditor checks cardinality)."""
    _, control = refdest_server
    engine = engine_factory()
    regs = []
    for i in range(3):
        reg = engine.send(
            "REGISTER " + contract(f"cr-reentrant-{i}", scope=f"scope-{i}")
        )
        regs.append(reg)
    # Truth split: records 0 and 2 get committed-but-lost; record 1 never lands.
    control.schedule(
        [
            {"match": {"client_ref": regs[0]["operation_id"]},
             "fault": "DROP_RESPONSE_AFTER_COMMIT"},
            {"match": {"client_ref": regs[1]["operation_id"]},
             "fault": "DROP_RESPONSE_BEFORE_COMMIT"},
            {"match": {"client_ref": regs[2]["operation_id"]},
             "fault": "DROP_RESPONSE_AFTER_COMMIT"},
        ]
    )
    for reg in regs:
        result = engine.send("DISPATCH " + reg["effect_id"])
        assert result["lifecycle"] == "AMBIGUOUS"
    engine.sigkill()
    engine.assert_died_by_sigkill()

    # Crash during recovery after the 1st record, then after the 2nd.
    for nth in ("1", "2"):
        crashing = engine_factory(
            {"DETENT_CRASH_AT": f"recovery.after_record:{nth}"}, wait_ready=False
        )
        crashing.assert_died_by_sigkill()

    engine_factory()  # completes recovery

    frontiers = {
        r["effect_id"]: r["frontier"]
        for r in _sql(
            fresh_db.admin_dsn, "SELECT effect_id, frontier FROM effect_frontiers"
        )
    }
    assert frontiers[regs[0]["effect_id"]] == "SETTLED_COMMITTED"
    assert frontiers[regs[1]["effect_id"]] == "SETTLED_FAILED"
    assert frontiers[regs[2]["effect_id"]] == "SETTLED_COMMITTED"
    assert len(control.state()) == 2, "crash count must not change effect count"

    findings = _sql(
        fresh_db.admin_dsn,
        "SELECT effect_id, classification, count(*) AS n FROM findings "
        "GROUP BY effect_id, classification",
    )
    assert all(f["n"] == 1 for f in findings), "no duplicate findings"
    by_effect = {f["effect_id"]: f["classification"] for f in findings}
    assert by_effect[regs[0]["effect_id"]] == "CONFIRMED_UNIQUE"
    assert by_effect[regs[1]["effect_id"]] == "LOST"
    assert by_effect[regs[2]["effect_id"]] == "CONFIRMED_UNIQUE"


def test_second_engine_process_is_refused_by_writer_lock(
    fresh_db: DBHandles,
    refdest_server: tuple[str, RefdestControl],
    engine_factory: Any,
) -> None:
    """§13: two engine processes — the boot advisory lock refuses the second
    (single-writer invariant enforced, not assumed)."""
    first = engine_factory()
    assert first.proc.poll() is None
    second = engine_factory(wait_ready=False)
    assert second.exit_code() == 3, "the second process must refuse to start"
