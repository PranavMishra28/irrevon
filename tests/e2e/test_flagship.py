"""The flagship E2E acceptance test — RFC-001 §9.5 / testing.md §9.

One automated test, two legs, the same frozen fault schedule, against the
reference destination (C2 profile). Leg R is the Irrevon story with explicit
assertions at every step (ledger via SQL; destination via the truth API — the
oracle is never the engine). Leg B5 is the honest contrast: the strongest
baseline operationalization produces a DUPLICATE, proven by read-back.

Conformance: master doc §12.1 rows 1-4 all execute inside this scenario; the
evidence bundle (ledger export + destination read-back + request logs) doubles
as the M8 attack-demo artifact.
"""

from __future__ import annotations

import hashlib
import json
from pathlib import Path
from typing import Any

import psycopg
import pytest
from psycopg.rows import dict_row

from irrevon.adapters.base import declarations_dir, load_declaration
from irrevon.adapters.refdest import RefDest, RefdestAdapter
from irrevon.api.baselines import B5DurableRuntime
from tests.integration.conftest import DBHandles
from tests.process.conftest import RefdestControl

pytestmark = pytest.mark.integration

# The frozen re-synthesis variant (fixture, not generated at test time).
ORIGINAL_PARAMS = {
    "line_items": [{"sku": "SKU-118", "quantity": 2}],
    "shipping_method": "standard",
}
RESYNTHESIZED_PARAMS = {
    "items": [{"sku": "SKU-118", "qty": 2}],
    "shipping": {"method": "standard"},
    "note": "retry of my earlier order request",
}
STABLE_IDS = {"order_id": "9410", "customer_ref": "C-0007"}
SCOPE = "acme-store/prod"
EFFECT_TYPE = "order.create"


def _contract(parameters: dict[str, Any], authority: str) -> str:
    from datetime import UTC, datetime

    return json.dumps(
        {
            "schema_version": "1",
            "stable_ids": dict(STABLE_IDS),
            "effect_type": EFFECT_TYPE,
            "effect_class": "IRREVERSIBLE",
            "scope": SCOPE,
            "adapter_id": "refdest-c2",
            "parameters": parameters,
            "authority_ref": authority,
            "stamped_at": datetime.now(UTC).isoformat().replace("+00:00", "Z"),
        }
    )


def _independent_intent_id() -> str:
    """A second implementation of the RFC-001 §1 derivation, written from the
    RFC text — NOT the engine's function (testing.md §9 step-1 oracle). For
    ASCII-only string members, JCS coincides with compact sorted-key JSON."""
    tuple_json = json.dumps(
        {"effect_type": EFFECT_TYPE, "scope": SCOPE, "stable_ids": STABLE_IDS},
        sort_keys=True,
        separators=(",", ":"),
        ensure_ascii=False,
    )
    return hashlib.sha256(tuple_json.encode()).hexdigest()


def _sql(dsn: str, query: str, params: tuple[Any, ...] = ()) -> list[dict[str, Any]]:
    with psycopg.connect(dsn, row_factory=dict_row) as conn:
        return [dict(r) for r in conn.execute(query, params).fetchall()]  # type: ignore[arg-type]


def test_flagship_leg_r_and_leg_b5(
    fresh_db: DBHandles,
    refdest_server: tuple[str, RefdestControl],
    engine_factory: Any,
    tmp_path: Path,
) -> None:
    base_url, control = refdest_server

    # ══ Leg R (Irrevon) — testing.md §9 steps 1-10 ═════════════════════════════

    # 1. registerIntent: effect_id equals the independently recomputed hash.
    engine = engine_factory()
    reg = engine.send("REGISTER " + _contract(ORIGINAL_PARAMS, "auth_approved_task_18"))
    assert reg["effect_id"] == _independent_intent_id(), (
        "identity oracle: in-test derivation from the RFC text must match"
    )
    assert reg["lifecycle"] == "PERSISTED"
    transitions = _sql(
        fresh_db.admin_dsn,
        "SELECT to_state FROM effect_transitions ORDER BY transition_seq",
    )
    assert [t["to_state"] for t in transitions] == ["INTENDED", "PERSISTED"]

    # 2-4. gate allow → dispatch → destination effect created, response lost
    # on cue → receipt LOST → AMBIGUOUS with evidence.
    control.schedule(
        [{"match": {"op": "create"}, "fault": "DROP_RESPONSE_AFTER_COMMIT"}]
    )
    result = engine.send("DISPATCH " + reg["effect_id"])
    assert result["lifecycle"] == "AMBIGUOUS"
    assert result["transport_outcome"] == "LOST"
    decisions = _sql(
        fresh_db.admin_dsn, "SELECT outcome FROM gate_decisions ORDER BY decision_id"
    )
    assert [d["outcome"] for d in decisions] == ["ALLOW"]
    effects = control.state()
    assert len(effects) == 1
    assert effects[0]["client_ref"] == reg["operation_id"], (
        "the stamped client reference derives from operation_id"
    )
    receipts = _sql(
        fresh_db.admin_dsn,
        "SELECT transport_outcome, evidence FROM dispatch_receipts",
    )
    assert receipts[0]["transport_outcome"] == "LOST"
    assert receipts[0]["evidence"]["evidence_digest"].startswith("sha256:")

    # 5. crash: real SIGKILL; exit status −9; destination count still 1.
    engine.sigkill()
    engine.assert_died_by_sigkill()
    assert len(control.state()) == 1
    log_before = len(control.log())

    # 6-8. restart: recovery scans BEFORE accepting work; reconcile-by-query;
    # SETTLED_COMMITTED + CONFIRMED_UNIQUE; auditor runs via the fixture.
    engine2 = engine_factory()
    assert any(s.startswith("RECOVERY DONE") for s in engine2.sentinels)
    new_ops = [r["op"] for r in control.log()[log_before:]]
    assert "query" in new_ops and "create" not in new_ops, (
        "status-query precedes any dispatch; no re-dispatch happened at all"
    )
    frontier = _sql(fresh_db.admin_dsn, "SELECT frontier FROM effect_frontiers")
    assert [f["frontier"] for f in frontier] == ["SETTLED_COMMITTED"]
    findings = _sql(
        fresh_db.admin_dsn, "SELECT classification, evidence FROM findings"
    )
    assert [f["classification"] for f in findings] == ["CONFIRMED_UNIQUE"]
    assert findings[0]["evidence"]["probe_ids"], "settle cites the probe evidence"

    # 9. re-synthesized retry: frozen variant, same stable ids → same intent_id.
    retry = engine2.send(
        "REGISTER " + _contract(RESYNTHESIZED_PARAMS, "auth_approved_task_22")
    )
    assert retry["effect_id"] == reg["effect_id"], "one effect_id — no second identity"
    assert retry["replayed"] is True
    assert retry["parameter_variant_digest"] is not None

    # 10. duplicate rejected with evidence; destination count still 1.
    deny = engine2.send("DISPATCH " + reg["effect_id"])
    assert deny["outcome"] == "denied"
    assert deny["deny_check"] == "dedup"
    assert deny["deny_evidence"]["blocking_executions"][0]["frontier"] == (
        "SETTLED_COMMITTED"
    )
    assert retry["parameter_variant_digest"] in deny["deny_evidence"][
        "parameter_variants"
    ], "the deny cites the recorded re-synthesis variant"
    assert len(control.state()) == 1
    receipts_after = _sql(fresh_db.admin_dsn, "SELECT count(*) AS n FROM dispatch_receipts")
    assert receipts_after[0]["n"] == 1, "no new receipt for the denied retry"
    engine2.close()

    # ══ Leg B5 (honest contrast) — identical schedule ═════════════════════════

    control.reset(seed=42)
    control.schedule(
        [{"match": {"op": "create"}, "fault": "DROP_RESPONSE_AFTER_COMMIT"}]
    )
    declaration = load_declaration(declarations_dir() / "refdest-c2.capability.json")
    adapter = RefdestAdapter("refdest-c2", declaration, base_url=base_url)
    journal = tmp_path / "b5-journal.json"

    b5 = B5DurableRuntime(journal, adapter)
    first = b5.execute("wf-order-9410-activity-0", EFFECT_TYPE, ORIGINAL_PARAMS)
    assert first["transport_outcome"] == "LOST"
    del b5  # crash: the runtime process dies; the durable journal survives

    recovered = B5DurableRuntime(journal, adapter)
    retried = recovered.recover()
    assert len(retried) == 1

    # ── THE PINNED ASSERTION (do not weaken; direction is load-bearing) ──────
    # This leg FAILS THE BUILD if B5 does not produce a duplicate (master doc
    # §8.6 falsification commitment; testing.md §9). If B5 stops failing here —
    # the destination accidentally honors keys, or B5 was configured
    # stronger/weaker than the preregistered operationalization — the flagship
    # claim's premise is wrong and MUST surface as red, never be patched to
    # keep the demo impressive.
    assert len(control.state()) == 2, (
        "B5 (stable op-ID + durable retry + idempotency key SENT) must produce "
        "a duplicate on the C2 destination — if it did not, the premise is "
        "broken: STOP and escalate (T-104 human-review trigger), do not patch"
    )


def test_of_the_test_b5_with_keys_honored_does_not_duplicate(
    tmp_path: Path,
) -> None:
    """The test-of-the-test (T-104 acceptance edge case): run the SAME B5
    operationalization against a destination that HONORS idempotency keys (C1
    profile). B5 then correctly does NOT duplicate — proving the contrast
    leg's assertion direction is real (it would fail red), not tautological."""
    declaration = load_declaration(declarations_dir() / "refdest-c1.capability.json")
    refdest = RefDest(seed=42, profile="C1")
    adapter = RefdestAdapter("refdest-c1", declaration, instance=refdest)
    refdest.control_schedule(
        [{"match": {"op": "create"}, "fault": "DROP_RESPONSE_AFTER_COMMIT"}]
    )
    journal = tmp_path / "b5-journal.json"

    b5 = B5DurableRuntime(journal, adapter)
    first = b5.execute("wf-order-9410-activity-0", EFFECT_TYPE, ORIGINAL_PARAMS)
    assert first["transport_outcome"] == "LOST"
    del b5
    recovered = B5DurableRuntime(journal, adapter)
    recovered.recover()

    n = len(refdest.control_state())
    assert n == 1, "with keys honored, B5's retry replays instead of duplicating"
    # And therefore the flagship contrast predicate (n == 2) evaluates False:
    # the E2E assertion above WOULD fail — the direction is pinned and honest.
    assert not (n == 2)
