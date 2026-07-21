"""Commit gate on real Postgres — order, evidence, and the §5.2 outcome map.

T-102 acceptance: gate order and evidence per RFC-002 §4 — every deny AND allow
writes a decision row; the dedup deny cites the blocking execution and the
recorded parameter variants (the re-synthesis defeat, master doc §8 flagship
mechanism).
"""

from __future__ import annotations

from datetime import UTC, datetime, timedelta
from typing import Any

import pytest

from irrevon.errors import IllegalState, ScopeBusy
from irrevon.ledger import Ledger
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
        "parameters": {"note": "original"},
        "authority_ref": "auth_1",
        "stamped_at": datetime.now(UTC).isoformat().replace("+00:00", "Z"),
    }
    raw.update(overrides)
    return raw


def _decisions(dsn: str, effect_id: str) -> list[dict[str, Any]]:
    with admin_conn(dsn) as conn:
        return [
            dict(r)
            for r in conn.execute(
                "SELECT * FROM gate_decisions WHERE effect_id = %s ORDER BY decision_id",
                (effect_id,),
            ).fetchall()
        ]


def test_allow_writes_decision_row_with_ordered_checks(fresh_db: DBHandles) -> None:
    with Ledger(fresh_db.app_dsn) as ledger:
        reg = ledger.register_intent(_raw(), DECL)
        claim = ledger.claim_dispatch(reg.effect_id)
    assert claim.outcome == "claimed"
    assert claim.idempotency_key == f"{reg.effect_id}:0"
    decisions = _decisions(fresh_db.admin_dsn, reg.effect_id)
    assert len(decisions) == 1
    d = decisions[0]
    assert d["outcome"] == "ALLOW"
    # Order pinned by RFC-001 §4: deny_list → authority → branch_lineage → dedup.
    assert [c["check"] for c in d["checks"]] == [
        "deny_list",
        "authority",
        "branch_lineage",
        "dedup",
    ]
    assert all(c["status"] == "passed" for c in d["checks"])
    assert d["evidence"]["input_digest"].startswith("sha256:")
    # Cleanly settle so the auditor sees a coherent end state.
    with Ledger(fresh_db.app_dsn) as ledger:
        assert claim.attempt_id is not None
        ledger.record_outcome(claim.attempt_id, "OK", destination_ref="dest_1")


def test_deny_list_aborts_first_and_is_evidenced(fresh_db: DBHandles) -> None:
    with admin_conn(fresh_db.admin_dsn) as conn:
        conn.execute(
            "INSERT INTO deny_entries (effect_class, reason) "
            "VALUES ('IRREVERSIBLE', 'incident containment drill')"
        )
    with Ledger(fresh_db.app_dsn) as ledger:
        reg = ledger.register_intent(_raw(), DECL)
        claim = ledger.claim_dispatch(reg.effect_id)
    assert claim.outcome == "denied"
    assert claim.deny_check == "deny_list"
    decisions = _decisions(fresh_db.admin_dsn, reg.effect_id)
    assert decisions[-1]["deny_check"] == "deny_list"
    statuses = {c["check"]: c["status"] for c in decisions[-1]["checks"]}
    assert statuses["deny_list"] == "denied"
    assert statuses["authority"] == "not_reached"  # abort-first semantics
    assert statuses["dedup"] == "not_reached"


def test_lifted_deny_entry_no_longer_denies(fresh_db: DBHandles) -> None:
    with admin_conn(fresh_db.admin_dsn) as conn:
        row = conn.execute(
            "INSERT INTO deny_entries (effect_class, reason) "
            "VALUES ('IRREVERSIBLE', 'drill') RETURNING deny_id"
        ).fetchone()
        assert row is not None
        conn.execute(
            "INSERT INTO deny_lifts (deny_id) VALUES (%s)", (row["deny_id"],)
        )
    with Ledger(fresh_db.app_dsn) as ledger:
        reg = ledger.register_intent(_raw(), DECL)
        claim = ledger.claim_dispatch(reg.effect_id)
        assert claim.outcome == "claimed"
        assert claim.attempt_id is not None
        ledger.record_outcome(claim.attempt_id, "OK", destination_ref="dest_1")


def test_expired_authority_denies_safe_abort(fresh_db: DBHandles) -> None:
    """Expiry between persist and dispatch → deny, safe abort (§7.4 item 4).
    Expiry here comes from the default policy: stamped_at + 24h < now."""
    stale = (datetime.now(UTC) - timedelta(hours=25)).isoformat().replace("+00:00", "Z")
    with Ledger(fresh_db.app_dsn) as ledger:
        reg = ledger.register_intent(_raw(stamped_at=stale), DECL)
        claim = ledger.claim_dispatch(reg.effect_id)
    assert claim.outcome == "denied"
    assert claim.deny_check == "authority"
    assert claim.deny_evidence is not None
    assert claim.deny_evidence["cause"] == "expired"
    # The record is still PERSISTED — nothing was dispatched.
    with Ledger(fresh_db.app_dsn) as ledger:
        assert ledger.effect_frontier(reg.effect_id)["frontier"] == "PERSISTED"


def test_branch_cancellation_denies_then_record_cancellable(
    fresh_db: DBHandles,
) -> None:
    """Branch cancelled after registration: gate check 3 denies at claim time."""
    with Ledger(fresh_db.app_dsn) as ledger:
        reg = ledger.register_intent(_raw(branch_ref="wf_late_cancel"), DECL)
    with admin_conn(fresh_db.admin_dsn) as conn:
        conn.execute(
            "INSERT INTO branch_cancellations (branch_ref, reason) "
            "VALUES ('wf_late_cancel', 'operator cancelled')"
        )
    with Ledger(fresh_db.app_dsn) as ledger:
        claim = ledger.claim_dispatch(reg.effect_id)
    assert claim.outcome == "denied"
    assert claim.deny_check == "branch_lineage"


def test_dedup_deny_cites_blocking_execution_and_variants(
    fresh_db: DBHandles,
) -> None:
    """The flagship re-synthesis defeat (RFC-002 §5.2): a settled effect +
    re-registered variant parameters ⇒ evidenced dedup deny citing the settled
    execution AND the recorded parameter variants. One effect_id throughout."""
    with Ledger(fresh_db.app_dsn) as ledger:
        reg = ledger.register_intent(_raw(), DECL)
        claim = ledger.claim_dispatch(reg.effect_id)
        assert claim.outcome == "claimed"
        assert claim.attempt_id is not None
        ledger.record_outcome(claim.attempt_id, "OK", destination_ref="dest_1")

        # Re-synthesized retry: different model arguments, same stable ids.
        retry = ledger.register_intent(_raw(parameters={"note": "retry v2"}), DECL)
        assert retry.effect_id == reg.effect_id  # no second identity
        assert retry.parameter_variant_digest is not None

        deny = ledger.claim_dispatch(reg.effect_id)
    assert deny.outcome == "denied"
    assert deny.deny_check == "dedup"
    assert deny.deny_evidence is not None
    blocking = deny.deny_evidence["blocking_executions"]
    assert len(blocking) == 1
    assert blocking[0]["frontier"] == "SETTLED_COMMITTED"
    assert blocking[0]["receipt_ids"], "deny must cite the settled receipts"
    assert deny.deny_evidence["parameter_variants"] == [
        retry.parameter_variant_digest
    ]
    # Both the allow and the deny wrote decision rows.
    decisions = _decisions(fresh_db.admin_dsn, reg.effect_id)
    assert [d["outcome"] for d in decisions] == ["ALLOW", "DENY"]


def test_dispatch_on_ambiguous_returns_pending_never_redispatches(
    fresh_db: DBHandles,
) -> None:
    """§5.2: DISPATCHED/AMBIGUOUS → pending_reconciliation; never re-dispatch
    on belief; no wire call; no new attempt row."""
    with Ledger(fresh_db.app_dsn) as ledger:
        reg = ledger.register_intent(_raw(), DECL)
        claim = ledger.claim_dispatch(reg.effect_id)
        assert claim.attempt_id is not None
        ledger.record_outcome(claim.attempt_id, "LOST", evidence={"drop": True})
        pending = ledger.claim_dispatch(reg.effect_id)
        assert pending.outcome == "pending_reconciliation"
        assert pending.lifecycle == "AMBIGUOUS"
        assert pending.last_receipt is not None
        assert pending.last_receipt["transport_outcome"] == "LOST"
        attempts = ledger.query(
            "SELECT count(*) AS n FROM dispatch_attempts a JOIN effect_executions e "
            "USING (execution_id) WHERE e.effect_id = %s",
            (reg.effect_id,),
        )
        assert attempts[0]["n"] == 1
        # Settle for the auditor (reconciled present).
        assert claim.execution_id is not None
        ledger.settle_ambiguous(
            claim.execution_id,
            "SETTLED_COMMITTED",
            "reconciled_present",
            "reconciler",
            {"probe_ids": [1]},
            classification="CONFIRMED_UNIQUE",
        )


def test_settled_failed_dispatch_is_retryable_failed_deny(
    fresh_db: DBHandles,
) -> None:
    """§5.2: SETTLED_FAILED → evidenced deny (dedup, subtype retryable_failed)
    pointing at the explicit retry operation; never a silent replay."""
    with Ledger(fresh_db.app_dsn) as ledger:
        reg = ledger.register_intent(_raw(), DECL)
        claim = ledger.claim_dispatch(reg.effect_id)
        assert claim.attempt_id is not None
        ledger.record_outcome(
            claim.attempt_id,
            "FAILED",
            failure_kind="TERMINAL",
            evidence={"destination_error": "card_declined"},
        )
        deny = ledger.claim_dispatch(reg.effect_id)
    assert deny.outcome == "denied"
    assert deny.deny_check == "dedup"
    assert deny.deny_subtype == "retryable_failed"
    assert deny.deny_evidence is not None
    assert deny.deny_evidence["retry_operation"] == "open_retry_execution"


def test_dispatch_on_cancelled_is_illegal_state(fresh_db: DBHandles) -> None:
    with admin_conn(fresh_db.admin_dsn) as conn:
        conn.execute(
            "INSERT INTO branch_cancellations (branch_ref, reason) "
            "VALUES ('wf_dead', 'dead')"
        )
    with Ledger(fresh_db.app_dsn) as ledger:
        reg = ledger.register_intent(_raw(branch_ref="wf_dead"), DECL)
        assert reg.lifecycle == "CANCELLED"
        with pytest.raises(IllegalState):
            ledger.claim_dispatch(reg.effect_id)


def test_open_attempt_in_slot_is_scope_busy(fresh_db: DBHandles) -> None:
    """One in-flight dispatch per (scope, effect_type), durable across crashes
    via the open-attempt row (§5.1) — a SECOND effect in the same slot gets the
    retryable slot_busy while the first attempt is open."""
    with Ledger(fresh_db.app_dsn) as ledger:
        first = ledger.register_intent(_raw(), DECL)
        second = ledger.register_intent(
            _raw(stable_ids={"order_id": "9999"}), DECL
        )
        claim = ledger.claim_dispatch(first.effect_id)
        assert claim.outcome == "claimed"
        with pytest.raises(ScopeBusy) as excinfo:
            ledger.claim_dispatch(second.effect_id)
        assert excinfo.value.retryable is True
        assert excinfo.value.details["blocking_effect_id"] == first.effect_id
        # Close the open attempt; the slot frees; the second effect claims.
        assert claim.attempt_id is not None
        ledger.record_outcome(claim.attempt_id, "OK", destination_ref="dest_1")
        retry = ledger.claim_dispatch(second.effect_id)
        assert retry.outcome == "claimed"
        assert retry.attempt_id is not None
        ledger.record_outcome(retry.attempt_id, "OK", destination_ref="dest_2")


def test_late_outcome_lands_in_late_responses(fresh_db: DBHandles) -> None:
    """§5.1: a losing T-OUTCOME is recorded, never dropped; a contradiction
    (settled FAILED, wire says OK) is flagged for audit — the C3' path."""
    with Ledger(fresh_db.app_dsn) as ledger:
        reg = ledger.register_intent(_raw(), DECL)
        claim = ledger.claim_dispatch(reg.effect_id)
        assert claim.attempt_id is not None
        first = ledger.record_outcome(
            claim.attempt_id, "FAILED", failure_kind="TERMINAL"
        )
        assert first.settled is True
        late = ledger.record_outcome(
            claim.attempt_id, "OK", destination_ref="dest_late"
        )
        assert late.settled is False
        assert late.contradicts_settle is True
        rows = ledger.query(
            "SELECT contradicts_settle FROM late_responses WHERE attempt_id = %s",
            (claim.attempt_id,),
        )
        assert rows and rows[0]["contradicts_settle"] is True
