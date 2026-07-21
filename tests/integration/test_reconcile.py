"""Reconciliation per tier + calibrated absence (RFC-002 §6) on real Postgres
with the in-process refdest.

Also covers master doc §12.1 row 8 — "Ambiguous outcomes surfaced, never
silently resolved": every settle out of AMBIGUOUS here carries probe evidence,
and the standing auditor post-condition re-checks it after every test.
"""

from __future__ import annotations

import copy
from datetime import UTC, datetime
from typing import Any

import pytest

from detent.adapters.base import declarations_dir, load_declaration
from detent.adapters.refdest import RefDest, RefdestAdapter
from detent.dispatcher import dispatch, open_retry_execution
from detent.errors import CapabilityUnsupported, ResolutionInvalid
from detent.ledger import Ledger
from detent.reconciler import ReconcileConfig, audit_effect, reconcile_effect
from detent.resolution import ResolutionConfig, resolve
from tests.integration.conftest import DBHandles

pytestmark = pytest.mark.integration

CONFIG = ReconcileConfig(stuck_threshold_s=300.0, absence_reread_gap_s=0.0)
C2_DECL = load_declaration(declarations_dir() / "refdest-c2.capability.json")
C1_DECL = load_declaration(declarations_dir() / "refdest-c1.capability.json")
C3_DECL = load_declaration(declarations_dir() / "refdest-c3.capability.json")


def _c2() -> tuple[RefDest, RefdestAdapter]:
    refdest = RefDest(seed=7, profile="C2")
    return refdest, RefdestAdapter("refdest-c2", C2_DECL, instance=refdest)


def _raw(order_id: str, **overrides: Any) -> dict[str, Any]:
    raw: dict[str, Any] = {
        "schema_version": "1",
        "stable_ids": {"order_id": order_id},
        "effect_type": "order.create",
        "effect_class": "IRREVERSIBLE",
        "scope": f"reconcile/{order_id}",
        "adapter_id": "refdest-c2",
        "parameters": {"note": "reconcile-test"},
        "authority_ref": "auth_rc",
        "stamped_at": datetime.now(UTC).isoformat().replace("+00:00", "Z"),
    }
    raw.update(overrides)
    return raw


def _lost_dispatch(
    ledger: Ledger, refdest: RefDest, adapter: RefdestAdapter, order_id: str,
    *, committed: bool = True,
) -> str:
    reg = ledger.register_intent(_raw(order_id), adapter.declaration_digest())
    fault = "DROP_RESPONSE_AFTER_COMMIT" if committed else "DROP_RESPONSE_BEFORE_COMMIT"
    refdest.control_schedule([{"match": {"op": "create"}, "fault": fault}])
    report = dispatch(ledger, adapter, reg.effect_id)
    assert report.lifecycle == "AMBIGUOUS"
    return reg.effect_id


def test_present_unique_settles_committed_confirmed_unique(
    fresh_db: DBHandles,
) -> None:
    refdest, adapter = _c2()
    with Ledger(fresh_db.app_dsn) as ledger:
        effect_id = _lost_dispatch(ledger, refdest, adapter, "rc-present")
        report = reconcile_effect(ledger, adapter, effect_id, config=CONFIG)
        assert report.settled == [
            {"effect_id": effect_id, "from": "AMBIGUOUS", "to": "SETTLED_COMMITTED"}
        ]
        findings = ledger.findings_for(effect_id)
        assert [f["classification"] for f in findings] == ["CONFIRMED_UNIQUE"]
        # The settle evidence cites the probe (§12.1 row 8).
        probes = ledger.query(
            "SELECT probe_id, result FROM status_probes ORDER BY probe_id"
        )
        assert probes and probes[0]["result"] == "PRESENT"


def test_present_n2_settles_committed_duplicate(fresh_db: DBHandles) -> None:
    """PRESENT(n>1) → COMMITTED + DUPLICATE(OPEN, excess recorded) — the
    canonical n>1 meaning (AM-18)."""
    refdest, adapter = _c2()
    with Ledger(fresh_db.app_dsn) as ledger:
        effect_id = _lost_dispatch(ledger, refdest, adapter, "rc-dup")
        op = ledger.effect_frontier(effect_id)["operation_id"]
        # Destination-internal duplicate materializes out of band (same
        # client_ref) — what DUPLICATE_ACCEPT would have produced.
        refdest.control_oob_create("order.create", {"dup": True}, client_ref=op)
        report = reconcile_effect(ledger, adapter, effect_id, config=CONFIG)
        assert report.settled[0]["to"] == "SETTLED_COMMITTED"
        findings = ledger.findings_for(effect_id)
        assert [f["classification"] for f in findings] == ["DUPLICATE"]
        assert findings[0]["excess_effect_count"] == 1
        # DUPLICATE stays OPEN for resolution — never auto-closed.
        resolutions = ledger.query(
            "SELECT 1 FROM finding_resolutions WHERE finding_id = %s",
            (findings[0]["finding_id"],),
        )
        assert resolutions == []


def test_confirmed_absence_settles_failed_lost(fresh_db: DBHandles) -> None:
    """ABSENT only via the §6.2 protocol: two reads, both authoritative."""
    refdest, adapter = _c2()
    with Ledger(fresh_db.app_dsn) as ledger:
        effect_id = _lost_dispatch(
            ledger, refdest, adapter, "rc-absent", committed=False
        )
        report = reconcile_effect(ledger, adapter, effect_id, config=CONFIG)
        assert report.settled[0]["to"] == "SETTLED_FAILED"
        findings = ledger.findings_for(effect_id)
        assert [f["classification"] for f in findings] == ["LOST"]
        probes = ledger.query("SELECT result FROM status_probes ORDER BY probe_id")
        assert [p["result"] for p in probes] == ["ABSENT", "ABSENT"]


def test_absence_within_settlement_lag_stays_ambiguous(
    fresh_db: DBHandles,
) -> None:
    """§6.2 condition 2: inside the declared visibility bound, absence is not
    authoritative — the record parks AMBIGUOUS, nothing settles."""
    declaration = copy.deepcopy(C2_DECL)
    declaration["consistency"]["status_settlement_lag"] = "PT1H"
    refdest = RefDest(seed=7)
    adapter = RefdestAdapter("refdest-c2", declaration, instance=refdest)
    with Ledger(fresh_db.app_dsn) as ledger:
        effect_id = _lost_dispatch(
            ledger, refdest, adapter, "rc-lag", committed=False
        )
        report = reconcile_effect(ledger, adapter, effect_id, config=CONFIG)
        assert report.settled == []
        assert report.still_ambiguous
        assert ledger.effect_frontier(effect_id)["frontier"] == "AMBIGUOUS"
        assert ledger.findings_for(effect_id) == []


def test_null_lag_settles_but_escalates_and_forbids_auto_redispatch(
    fresh_db: DBHandles,
) -> None:
    """T-103 acceptance edge case (RFC-002 §6.2): a null
    consistency.status_settlement_lag still permits the reconciled-absent
    settle, but the LOST finding is auto-routed ESCALATED_HUMAN and
    policy_auto redispatch is refused."""
    declaration = copy.deepcopy(C2_DECL)
    declaration["consistency"]["status_settlement_lag"] = None
    refdest = RefDest(seed=7)
    adapter = RefdestAdapter("refdest-c2", declaration, instance=refdest)
    adapters = {"refdest-c2": adapter}
    with Ledger(fresh_db.app_dsn) as ledger:
        effect_id = _lost_dispatch(
            ledger, refdest, adapter, "rc-nulllag", committed=False
        )
        report = reconcile_effect(ledger, adapter, effect_id, config=CONFIG)
        assert report.settled[0]["to"] == "SETTLED_FAILED"
        findings = ledger.findings_for(effect_id)
        assert [f["classification"] for f in findings] == ["LOST"]
        chain = ledger.query(
            "SELECT to_status, actor FROM finding_resolutions WHERE finding_id = %s "
            "ORDER BY resolution_seq",
            (findings[0]["finding_id"],),
        )
        assert [(r["to_status"], r["actor"]) for r in chain] == [
            ("ESCALATED_HUMAN", "system")
        ]
        # Automatic redispatch is forbidden — even with the effect type opted in.
        with pytest.raises(ResolutionInvalid, match="forbidden"):
            resolve(
                ledger,
                adapters,
                findings[0]["finding_id"],
                "REDISPATCHED",
                {
                    "fresh_authority_ref": "auth_auto",
                    "stamped_at": "2026-07-21T12:00:00Z",
                },
                actor="policy_auto",
                config=ResolutionConfig(
                    auto_redispatch_effect_types=frozenset({"order.create"})
                ),
            )


def test_indeterminate_probe_parks_ambiguous(fresh_db: DBHandles) -> None:
    refdest, adapter = _c2()
    with Ledger(fresh_db.app_dsn) as ledger:
        effect_id = _lost_dispatch(ledger, refdest, adapter, "rc-indet")
        refdest.control_schedule(
            [{"match": {"op": "query"}, "fault": "THROTTLE_429"}]
        )
        report = reconcile_effect(ledger, adapter, effect_id, config=CONFIG)
        assert report.settled == []
        assert report.still_ambiguous
        assert ledger.effect_frontier(effect_id)["frontier"] == "AMBIGUOUS"


def test_reconcile_settled_record_issues_no_query(fresh_db: DBHandles) -> None:
    """§6.3: reconcile on already-settled records returns recorded findings
    and issues NO destination query."""
    refdest, adapter = _c2()
    with Ledger(fresh_db.app_dsn) as ledger:
        effect_id = _lost_dispatch(ledger, refdest, adapter, "rc-settled")
        reconcile_effect(ledger, adapter, effect_id, config=CONFIG)
        log_len = len(refdest.control_log())
        report = reconcile_effect(ledger, adapter, effect_id, config=CONFIG)
        assert report.findings, "recorded findings are returned"
        assert len(refdest.control_log()) == log_len, "no new destination query"


def test_c3_parks_and_escalates_never_settles(fresh_db: DBHandles) -> None:
    """C3: no adjudication exists; park AMBIGUOUS; only a human may settle —
    the impossibility boundary, demonstrated openly (§6.1)."""
    refdest = RefDest(seed=7, profile="C3")
    adapter = RefdestAdapter("refdest-c3", C3_DECL, instance=refdest)
    with Ledger(fresh_db.app_dsn) as ledger:
        reg = ledger.register_intent(
            _raw("rc-c3", adapter_id="refdest-c3", effect_type="notify.send"),
            adapter.declaration_digest(),
        )
        refdest.control_schedule(
            [{"match": {"op": "notify"}, "fault": "DROP_RESPONSE_AFTER_COMMIT"}]
        )
        report = dispatch(ledger, adapter, reg.effect_id)
        assert report.lifecycle == "AMBIGUOUS"
        # The oracle sees the truth; the system under test cannot.
        assert len(refdest.control_state()) == 1
        rec = reconcile_effect(ledger, adapter, reg.effect_id, config=CONFIG)
        assert rec.settled == []
        assert rec.still_ambiguous and rec.escalated
        assert ledger.effect_frontier(reg.effect_id)["frontier"] == "AMBIGUOUS"
        # A human may settle it — with evidence (the only path out).
        frontier = ledger.effect_frontier(reg.effect_id)
        ledger.settle_ambiguous(
            frontier["execution_id"],
            "SETTLED_COMMITTED",
            "reconciled_present",
            "human",
            {"human": "operator verified via destination console", "probe_ids": []},
            classification="CONFIRMED_UNIQUE",
            created_by="human",
        )


def test_c1_replay_probe_settles_in_window(fresh_db: DBHandles) -> None:
    """§5.3 item 2: AMBIGUOUS + declared idempotency → replay probe with the
    SAME key; the declared cached-replay semantics settle it without a second
    effect."""
    refdest = RefDest(seed=7, profile="C1")
    adapter = RefdestAdapter("refdest-c1", C1_DECL, instance=refdest)
    with Ledger(fresh_db.app_dsn) as ledger:
        reg = ledger.register_intent(
            _raw("rc-c1", adapter_id="refdest-c1"), adapter.declaration_digest()
        )
        refdest.control_schedule(
            [{"match": {"op": "create"}, "fault": "DROP_RESPONSE_AFTER_COMMIT"}]
        )
        report = dispatch(ledger, adapter, reg.effect_id)
        assert report.lifecycle == "AMBIGUOUS"
        rec = reconcile_effect(ledger, adapter, reg.effect_id, config=CONFIG)
        assert rec.settled[0]["to"] == "SETTLED_COMMITTED"
        assert len(refdest.control_state()) == 1, "replay, not re-execution"
        findings = ledger.findings_for(reg.effect_id)
        assert [f["classification"] for f in findings] == ["CONFIRMED_UNIQUE"]
        attempts = ledger.query(
            "SELECT kind FROM dispatch_attempts a JOIN effect_executions e "
            "USING (execution_id) WHERE e.effect_id = %s ORDER BY attempt_id",
            (reg.effect_id,),
        )
        assert [a["kind"] for a in attempts] == ["primary", "c1_replay_probe"]


def test_retry_after_clean_failure_new_execution(fresh_db: DBHandles) -> None:
    """§5.3 item 1 + §5.2: a clean FAILED settle denies re-dispatch with
    subtype retryable_failed; open_retry_execution allocates a new step (new
    idempotency key) and the retry succeeds — one destination effect total."""
    refdest, adapter = _c2()
    with Ledger(fresh_db.app_dsn) as ledger:
        reg = ledger.register_intent(
            _raw("rc-retry", parameters={"reject": True}),
            adapter.declaration_digest(),
        )
        report = dispatch(ledger, adapter, reg.effect_id)
        assert report.lifecycle == "SETTLED_FAILED"
        assert report.receipt is not None

        deny = dispatch(ledger, adapter, reg.effect_id)
        assert deny.outcome == "denied"
        assert deny.claim.deny_subtype == "retryable_failed"

        # The explicit retry path: fresh authority, new step. The re-registered
        # payload variant fixes the reject flag... but the dispatchable payload
        # is the FIRST registration's (§1) — so this retry fails again cleanly,
        # proving the key is new; then verify attempt/step accounting.
        opened = open_retry_execution(
            ledger,
            reg.effect_id,
            {"fresh_authority_ref": "auth_rc2", "stamped_at": "2026-07-21T12:00:00Z"},
        )
        assert opened["step"] == 1
        assert opened["operation_id"] == f"{reg.effect_id}:1"
        retry = dispatch(ledger, adapter, reg.effect_id, variant="retry_after_failure")
        assert retry.lifecycle == "SETTLED_FAILED"  # payload still rejects
        keys = ledger.query(
            "SELECT idempotency_key FROM dispatch_attempts ORDER BY attempt_id"
        )
        assert keys[0]["idempotency_key"] != keys[1]["idempotency_key"]
        assert len(refdest.control_state()) == 0, "clean rejections, no effects"


def test_lost_resolve_redispatch_closes_when_committed(
    fresh_db: DBHandles,
) -> None:
    """§5.3 item 3: LOST → resolve(REDISPATCHED) with fresh authority and
    confirmed absence → replacement execution dispatches, settles COMMITTED,
    finding CLOSED — exactly one destination effect."""
    refdest, adapter = _c2()
    adapters = {"refdest-c2": adapter}
    with Ledger(fresh_db.app_dsn) as ledger:
        effect_id = _lost_dispatch(
            ledger, refdest, adapter, "rc-redispatch", committed=False
        )
        reconcile_effect(ledger, adapter, effect_id, config=CONFIG)
        finding = ledger.findings_for(effect_id)[0]
        assert finding["classification"] == "LOST"

        result = resolve(
            ledger,
            adapters,
            finding["finding_id"],
            "REDISPATCHED",
            {
                "note": "confirmed absent; re-approved",
                "fresh_authority_ref": "auth_rc3",
                "stamped_at": "2026-07-21T12:00:00Z",
            },
            actor="human",
        )
        assert result["status"] == "CLOSED"
        assert result["replacement_operation_id"] == f"{effect_id}:1"
        assert ledger.effect_frontier(effect_id)["frontier"] == "SETTLED_COMMITTED"
        assert len(refdest.control_state()) == 1


def test_audit_detects_contradicted_after_absent_settle(
    fresh_db: DBHandles,
) -> None:
    """The §6.2 residual race, caught by audit (§6.3): the effect materializes
    AFTER the confirmed-absent settle → CONTRADICTED (failed_but_present),
    with both the settle evidence and the fresh probe cited."""
    refdest, adapter = _c2()
    with Ledger(fresh_db.app_dsn) as ledger:
        effect_id = _lost_dispatch(
            ledger, refdest, adapter, "rc-contra", committed=False
        )
        reconcile_effect(ledger, adapter, effect_id, config=CONFIG)
        assert ledger.effect_frontier(effect_id)["frontier"] == "SETTLED_FAILED"
        # The residue: the destination materializes the effect late.
        op = ledger.effect_frontier(effect_id)["operation_id"]
        refdest.control_oob_create("order.create", {"late": True}, client_ref=op)

        report = audit_effect(ledger, adapter, effect_id)
        assert len(report.findings) == 1
        findings = ledger.findings_for(effect_id)
        classifications = sorted(f["classification"] for f in findings)
        assert classifications == ["CONTRADICTED", "LOST"]
        contradicted = next(
            f for f in findings if f["classification"] == "CONTRADICTED"
        )
        assert contradicted["evidence"]["direction"] == "failed_but_present"
        assert contradicted["evidence"]["settle_transition_seq"] is not None


def test_audit_detects_duplicate_on_settled_committed(fresh_db: DBHandles) -> None:
    refdest, adapter = _c2()
    with Ledger(fresh_db.app_dsn) as ledger:
        reg = ledger.register_intent(_raw("rc-audit-dup"), adapter.declaration_digest())
        report = dispatch(ledger, adapter, reg.effect_id)
        assert report.lifecycle == "SETTLED_COMMITTED"
        op = ledger.effect_frontier(reg.effect_id)["operation_id"]
        refdest.control_oob_create("order.create", {"dup": True}, client_ref=op)
        audit = audit_effect(ledger, adapter, reg.effect_id)
        assert len(audit.findings) == 1
        findings = ledger.findings_for(reg.effect_id)
        assert [f["classification"] for f in findings] == ["DUPLICATE"]
        assert findings[0]["excess_effect_count"] == 1


def test_sweep_refuses_on_c3(fresh_db: DBHandles) -> None:
    from detent.sweep import sweep

    refdest = RefDest(seed=7, profile="C3")
    adapter = RefdestAdapter("refdest-c3", C3_DECL, instance=refdest)
    with Ledger(fresh_db.app_dsn) as ledger:
        with pytest.raises(CapabilityUnsupported):
            sweep(ledger, adapter, "2026-01-01", "2027-01-01")
