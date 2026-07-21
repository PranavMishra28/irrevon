"""Dispatcher — the wire half of the claim protocol (RFC-002 §5).

``dispatch()`` implements the full §5.2 outcome map: claim → wire → outcome for
PERSISTED; pending_reconciliation for in-flight; evidenced dedup deny for
settled; illegal_state for CANCELLED. The wire call happens strictly AFTER the
claim transaction commits — no transaction open, no lock held across I/O.

``open_retry_execution()`` is §5.3 item 1: the only path to a new execution
after a clean SETTLED_FAILED — new step ⇒ new operation_id ⇒ new idempotency
key; the full gate runs on the new execution.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from irrevon.adapters.base import Adapter, DispatchOrder
from irrevon.errors import IllegalState, ResolutionInvalid
from irrevon.identity import canonical_digest
from irrevon.ledger import ClaimOutcome, Ledger, OutcomeRecord
from irrevon.testhooks import crashpoint, syncpoint

__all__ = ["DispatchReport", "dispatch", "open_retry_execution"]

DEFAULT_DISPATCH_DEADLINE_S = 30.0  # RFC-002 §13 tunable [DD]


@dataclass(frozen=True, slots=True)
class DispatchReport:
    """Discriminated union on ``outcome`` (dx-api §2.2)."""

    outcome: str  # dispatched | denied | pending_reconciliation
    effect_id: str
    lifecycle: str
    claim: ClaimOutcome
    receipt: OutcomeRecord | None = None
    transport_outcome: str | None = None
    destination_ref: str | None = None


def dispatch(
    ledger: Ledger,
    adapter: Adapter,
    effect_id: str,
    *,
    variant: str = "dispatch",
    kind: str = "primary",
    deadline_s: float = DEFAULT_DISPATCH_DEADLINE_S,
    waive_execution_id: int | None = None,
) -> DispatchReport:
    record = ledger.effect_record(effect_id)
    request_digest = canonical_digest(
        {
            "effect_type": record["effect_type"],
            "payload_digest": canonical_digest(dict(record["parameters"])),
        }
    )

    claim = ledger.claim_dispatch(
        effect_id,
        variant=variant,
        kind=kind,
        request_digest=request_digest,
        waive_execution_id=waive_execution_id,
    )
    if claim.outcome != "claimed":
        return DispatchReport(
            outcome=claim.outcome,
            effect_id=effect_id,
            lifecycle=claim.lifecycle,
            claim=claim,
        )

    # The claim transaction has committed; the durable open-attempt row exists.
    crashpoint("gate.post_allow")
    assert claim.operation_id is not None and claim.idempotency_key is not None
    assert claim.attempt_id is not None
    order = DispatchOrder(
        operation_id=claim.operation_id,
        effect_type=record["effect_type"],
        payload=dict(record["parameters"]),
        client_ref=claim.idempotency_key,
    )
    syncpoint("adapter.pre_call")
    crashpoint("adapter.pre_call")
    result = adapter.dispatch(order, deadline_s)
    syncpoint("adapter.post_call")

    outcome = ledger.record_outcome(
        claim.attempt_id,
        result.transport_outcome,
        failure_kind=result.failure_kind,
        destination_ref=result.destination_ref,
        response_digest=result.response_digest,
        evidence=result.evidence,
        recorded_by="dispatcher",
    )
    return DispatchReport(
        outcome="dispatched",
        effect_id=effect_id,
        lifecycle=outcome.lifecycle,
        claim=claim,
        receipt=outcome,
        transport_outcome=result.transport_outcome,
        destination_ref=result.destination_ref,
    )


def open_retry_execution(
    ledger: Ledger, effect_id: str, authority_evidence: dict[str, Any]
) -> dict[str, Any]:
    """§5.3 item 1: legal only when the latest execution is SETTLED_FAILED with
    a CLEAN (declaration-cited) failure — a reused key would replay the cached
    error on C1 and is meaningless on C2. Requires fresh authority evidence."""
    frontier = ledger.effect_frontier(effect_id)
    if frontier["frontier"] != "SETTLED_FAILED":
        raise IllegalState(
            "retry_after_failure requires a SETTLED_FAILED latest execution "
            f"(found {frontier['frontier']})"
        )
    receipt = ledger.latest_receipt(frontier["execution_id"])
    if receipt is None or receipt["transport_outcome"] != "FAILED":
        raise IllegalState(
            "retry_after_failure requires a clean, declaration-cited failure "
            "receipt; a reconciled-absent settle goes through resolve() instead"
        )
    fresh_ref = authority_evidence.get("fresh_authority_ref")
    stamped_at = authority_evidence.get("stamped_at")
    if not fresh_ref or not stamped_at:
        raise ResolutionInvalid(
            "retry requires fresh authority evidence "
            "(fresh_authority_ref + stamped_at)"
        )
    ledger.append_authority(effect_id, str(fresh_ref), str(stamped_at))
    return ledger.open_execution(effect_id, "retry_after_failure")
