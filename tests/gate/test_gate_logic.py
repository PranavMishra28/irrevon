"""Pure gate decision logic (RFC-002 §4) — no I/O; the ledger integration
tests cover the recorded-decision discipline."""

from __future__ import annotations

from datetime import UTC, datetime, timedelta

import pytest

from detent.gate import (
    AuthorityView,
    BlockingExecution,
    DenyEntryView,
    GateInputs,
    evaluate,
)

NOW = datetime(2026, 7, 21, 12, 0, 0, tzinfo=UTC)


def _inputs(**overrides: object) -> GateInputs:
    base: dict[str, object] = {
        "variant": "dispatch",
        "effect_id": "a" * 64,
        "effect_class": "IRREVERSIBLE",
        "effect_type": "order.create",
        "scope": "s1",
        "branch_ref": None,
        "now": NOW,
        "deny_entries": (),
        "authority": AuthorityView(
            authority_id=1,
            authority_ref="auth_1",
            scope="s1",
            stamped_at=NOW - timedelta(hours=1),
            effective_expires_at=NOW + timedelta(hours=23),
        ),
        "branch_cancelled": False,
        "executions": (
            BlockingExecution(
                execution_id=1, step=0, operation_id="a" * 64 + ":0", frontier="PERSISTED"
            ),
        ),
        "parameter_variants": (),
        "waive_execution_id": None,
    }
    base.update(overrides)
    return GateInputs(**base)  # type: ignore[arg-type]


def test_all_checks_pass_allows() -> None:
    decision = evaluate(_inputs())
    assert decision.outcome == "ALLOW"
    assert [c["check"] for c in decision.checks] == [
        "deny_list",
        "authority",
        "branch_lineage",
        "dedup",
    ]
    assert all(c["status"] == "passed" for c in decision.checks)


def test_deny_list_aborts_first() -> None:
    decision = evaluate(
        _inputs(
            deny_entries=(
                DenyEntryView(1, "IRREVERSIBLE", None, None, "incident"),
            )
        )
    )
    assert decision.outcome == "DENY"
    assert decision.deny_check == "deny_list"
    statuses = [c["status"] for c in decision.checks]
    assert statuses == ["denied", "not_reached", "not_reached", "not_reached"]


def test_missing_authority_denies() -> None:
    decision = evaluate(_inputs(authority=None))
    assert decision.deny_check == "authority"
    assert decision.evidence["cause"] == "no_authority"


def test_authority_scope_binding_mismatch_denies() -> None:
    decision = evaluate(
        _inputs(
            authority=AuthorityView(1, "auth_1", "OTHER", NOW, NOW + timedelta(hours=1))
        )
    )
    assert decision.deny_check == "authority"
    assert decision.evidence["cause"] == "scope_binding_mismatch"


def test_authority_without_derivable_expiry_denies() -> None:
    """Expiry = issuer expires_at, else stamped_at + policy max_age, else DENY
    (RFC-002 §2.2 authority model)."""
    decision = evaluate(
        _inputs(authority=AuthorityView(1, "auth_1", "s1", NOW, None))
    )
    assert decision.deny_check == "authority"
    assert decision.evidence["cause"] == "no_expiry_derivable"


def test_expired_authority_denies() -> None:
    decision = evaluate(
        _inputs(
            authority=AuthorityView(
                1, "auth_1", "s1", NOW - timedelta(days=2), NOW - timedelta(days=1)
            )
        )
    )
    assert decision.deny_check == "authority"
    assert decision.evidence["cause"] == "expired"


def test_branch_cancellation_denies_third() -> None:
    decision = evaluate(_inputs(branch_ref="wf_1", branch_cancelled=True))
    assert decision.deny_check == "branch_lineage"
    statuses = [c["status"] for c in decision.checks]
    assert statuses == ["passed", "passed", "denied", "not_reached"]


def test_dedup_denies_on_blocking_frontiers() -> None:
    for frontier in ("DISPATCHED", "AMBIGUOUS", "SETTLED_COMMITTED"):
        decision = evaluate(
            _inputs(
                executions=(
                    BlockingExecution(1, 0, "a" * 64 + ":0", frontier, (7,), (3,)),
                ),
                parameter_variants=("sha256:variant",),
            )
        )
        assert decision.outcome == "DENY"
        assert decision.deny_check == "dedup"
        assert decision.evidence["blocking_executions"][0]["frontier"] == frontier
        assert decision.evidence["blocking_executions"][0]["receipt_ids"] == [7]
        assert decision.evidence["parameter_variants"] == ["sha256:variant"]


def test_dedup_ignores_settled_failed_and_cancelled() -> None:
    decision = evaluate(
        _inputs(
            executions=(
                BlockingExecution(1, 0, "a" * 64 + ":0", "SETTLED_FAILED"),
                BlockingExecution(2, 1, "a" * 64 + ":1", "PERSISTED"),
            )
        )
    )
    assert decision.outcome == "ALLOW"


def test_recovery_redispatch_waives_only_self_match() -> None:
    """RFC-002 §4: recovery_redispatch waives the self-match on the
    just-settled execution — other blockers still deny."""
    settled = BlockingExecution(1, 0, "a" * 64 + ":0", "SETTLED_COMMITTED")
    decision = evaluate(
        _inputs(
            variant="recovery_redispatch",
            executions=(settled,),
            waive_execution_id=1,
        )
    )
    assert decision.outcome == "ALLOW"
    other = BlockingExecution(2, 1, "a" * 64 + ":1", "AMBIGUOUS")
    decision = evaluate(
        _inputs(
            variant="recovery_redispatch",
            executions=(settled, other),
            waive_execution_id=1,
        )
    )
    assert decision.outcome == "DENY"
    assert decision.deny_check == "dedup"


def test_unknown_variant_rejected() -> None:
    with pytest.raises(ValueError):
        evaluate(_inputs(variant="freestyle"))
