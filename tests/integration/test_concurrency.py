"""Concurrency edge cases on real Postgres (RFC-002 §13; testing.md §5.1).

Two engine workers = two Ledger instances on separate connections, released
from a barrier. No sleeps: outcomes are arbitered by the identity insert, the
slot/identity row locks, and the locked transition functions.
"""

from __future__ import annotations

import threading
from datetime import UTC, datetime
from typing import Any

import pytest

from irrevon.errors import IrrevonError, ScopeBusy
from irrevon.ledger import ClaimOutcome, Ledger, Registration
from tests.integration.conftest import DBHandles
from tests.integration.driver import admin_conn

pytestmark = pytest.mark.integration

DECL = "sha256:" + "d" * 64


def _raw(**overrides: Any) -> dict[str, Any]:
    raw: dict[str, Any] = {
        "schema_version": "1",
        "stable_ids": {"order_id": "9410"},
        "effect_type": "order.create",
        "effect_class": "IRREVERSIBLE",
        "scope": "acme-store/prod",
        "adapter_id": "refdest-c2",
        "parameters": {"note": "concurrent"},
        "authority_ref": "auth_1",
        "stamped_at": datetime.now(UTC).isoformat().replace("+00:00", "Z"),
    }
    raw.update(overrides)
    return raw


def test_concurrent_register_same_stable_ids(fresh_db: DBHandles) -> None:
    """§13 row 1: identity insert arbitered; the loser re-reads and returns the
    winner's effect_id; exactly one record and one execution exist."""
    barrier = threading.Barrier(2)
    results: list[Registration | Exception] = [None, None]  # type: ignore[list-item]

    def worker(i: int) -> None:
        with Ledger(fresh_db.app_dsn) as ledger:
            barrier.wait(timeout=10)
            try:
                results[i] = ledger.register_intent(_raw(), DECL)
            except Exception as err:  # pragma: no cover - diagnostic path
                results[i] = err

    threads = [threading.Thread(target=worker, args=(i,)) for i in range(2)]
    for t in threads:
        t.start()
    for t in threads:
        t.join(timeout=30)

    regs = [r for r in results if isinstance(r, Registration)]
    assert len(regs) == 2, f"unexpected failures: {results}"
    assert regs[0].effect_id == regs[1].effect_id
    assert sorted(r.replayed for r in regs) == [False, True]
    with admin_conn(fresh_db.admin_dsn) as conn:
        records = conn.execute("SELECT count(*) AS n FROM effect_records").fetchone()
        executions = conn.execute(
            "SELECT count(*) AS n FROM effect_executions"
        ).fetchone()
        assert records is not None and records["n"] == 1
        assert executions is not None and executions["n"] == 1


def test_concurrent_dispatch_same_effect(fresh_db: DBHandles) -> None:
    """§13 row 2: slot + identity locks serialize; the loser sees the open
    attempt (slot_busy) or the frontier (pending); exactly ONE attempt row —
    the destination effect count can never exceed 1."""
    with Ledger(fresh_db.app_dsn) as ledger:
        reg = ledger.register_intent(_raw(stable_ids={"order_id": "race"}), DECL)

    barrier = threading.Barrier(2)
    outcomes: list[ClaimOutcome | IrrevonError | None] = [None, None]

    def worker(i: int) -> None:
        with Ledger(fresh_db.app_dsn) as ledger:
            barrier.wait(timeout=10)
            try:
                outcomes[i] = ledger.claim_dispatch(reg.effect_id)
            except IrrevonError as err:
                outcomes[i] = err

    threads = [threading.Thread(target=worker, args=(i,)) for i in range(2)]
    for t in threads:
        t.start()
    for t in threads:
        t.join(timeout=30)

    claimed = [o for o in outcomes if isinstance(o, ClaimOutcome) and o.outcome == "claimed"]
    losers = [
        o
        for o in outcomes
        if isinstance(o, ScopeBusy)
        or (isinstance(o, ClaimOutcome) and o.outcome != "claimed")
    ]
    assert len(claimed) == 1, f"exactly one claim must win: {outcomes}"
    assert len(losers) == 1
    with admin_conn(fresh_db.admin_dsn) as conn:
        attempts = conn.execute("SELECT count(*) AS n FROM dispatch_attempts").fetchone()
        assert attempts is not None and attempts["n"] == 1

    with Ledger(fresh_db.app_dsn) as ledger:
        winner = claimed[0]
        assert winner.attempt_id is not None
        ledger.record_outcome(winner.attempt_id, "OK", destination_ref="dest_race")


def test_resynthesis_race_collapses_to_one_identity(fresh_db: DBHandles) -> None:
    """§13 row 1 variant: same stable ids arriving as different model payloads
    — identity derivation collapses them pre-gate."""
    barrier = threading.Barrier(2)
    results: list[Registration | None] = [None, None]

    def worker(i: int) -> None:
        with Ledger(fresh_db.app_dsn) as ledger:
            barrier.wait(timeout=10)
            results[i] = ledger.register_intent(
                _raw(parameters={"variant": f"model-wording-{i}"}), DECL
            )

    threads = [threading.Thread(target=worker, args=(i,)) for i in range(2)]
    for t in threads:
        t.start()
    for t in threads:
        t.join(timeout=30)

    assert results[0] is not None and results[1] is not None
    assert results[0].effect_id == results[1].effect_id
    with admin_conn(fresh_db.admin_dsn) as conn:
        records = conn.execute("SELECT count(*) AS n FROM effect_records").fetchone()
        assert records is not None and records["n"] == 1
        # The loser's divergent payload is recorded as a variant (evidence).
        variants = conn.execute(
            "SELECT count(*) AS n FROM parameter_variants"
        ).fetchone()
        assert variants is not None and variants["n"] == 1
