"""Commit gate — pure decision logic invoked inside the claim transaction.

Order pinned by RFC-001 §4 / RFC-002 §4 (cheapest/absolute first,
evidence-richest last): deny-list → authority freshness/binding → branch
lineage → dedup. Every evaluation — allow and deny — is recorded as a
``gate_decisions`` row by the ledger with the ordered check list and input
digests. The gate is deterministic conditional on clock inputs (RFC-002 §2.1):
same ledger state + same contract + same DB clock reading → same outcome.

Dedup (check 4) denies when ANY execution of this effect has frontier in
{DISPATCHED, AMBIGUOUS, SETTLED_COMMITTED}; the deny evidence cites the
blocking execution's transitions, receipts, findings, and recorded parameter
variants — the re-synthesis defeat, a first-class evidenced outcome, not an
error. Variant ``recovery_redispatch`` waives only the self-match on the
just-settled execution (RFC-002 §4).
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from typing import Any, Literal

from detent.identity import canonical_digest
from detent.statetable import GATE_CHECKS, GATE_VARIANTS

__all__ = [
    "AuthorityView",
    "BlockingExecution",
    "DenyEntryView",
    "GateDecision",
    "GateInputs",
    "evaluate",
]

DEDUP_BLOCKING_FRONTIERS = frozenset({"DISPATCHED", "AMBIGUOUS", "SETTLED_COMMITTED"})


@dataclass(frozen=True, slots=True)
class DenyEntryView:
    deny_id: int
    effect_class: str | None
    effect_type: str | None
    scope: str | None
    reason: str


@dataclass(frozen=True, slots=True)
class AuthorityView:
    """Latest authority bound to the effect, with the effective expiry already
    computed by the ledger (issuer expires_at, else stamped_at + policy
    max_age, else None ⇒ deny — RFC-002 §2.2 authority model)."""

    authority_id: int
    authority_ref: str
    scope: str
    stamped_at: datetime
    effective_expires_at: datetime | None


@dataclass(frozen=True, slots=True)
class BlockingExecution:
    execution_id: int
    step: int
    operation_id: str
    frontier: str
    receipt_ids: tuple[int, ...] = ()
    finding_ids: tuple[int, ...] = ()


@dataclass(frozen=True, slots=True)
class GateInputs:
    variant: str
    effect_id: str
    effect_class: str
    effect_type: str
    scope: str
    branch_ref: str | None
    now: datetime  # the DB clock reading — the single time authority
    deny_entries: tuple[DenyEntryView, ...]
    authority: AuthorityView | None
    branch_cancelled: bool
    executions: tuple[BlockingExecution, ...]  # ALL executions with frontiers
    parameter_variants: tuple[str, ...]  # recorded variant digests
    waive_execution_id: int | None = None  # recovery_redispatch self-match waiver


@dataclass(frozen=True, slots=True)
class GateDecision:
    outcome: Literal["ALLOW", "DENY"]
    deny_check: str | None
    checks: list[dict[str, Any]] = field(default_factory=list)
    evidence: dict[str, Any] = field(default_factory=dict)


def _deny_list_check(inputs: GateInputs) -> dict[str, Any] | None:
    hits = [
        {"deny_id": d.deny_id, "reason": d.reason}
        for d in inputs.deny_entries
        if (d.effect_class is None or d.effect_class == inputs.effect_class)
        and (d.effect_type is None or d.effect_type == inputs.effect_type)
        and (d.scope is None or d.scope == inputs.scope)
    ]
    return {"deny_entries": hits} if hits else None


def _authority_check(inputs: GateInputs) -> dict[str, Any] | None:
    a = inputs.authority
    if a is None:
        return {"cause": "no_authority"}
    if a.scope != inputs.scope:
        return {
            "cause": "scope_binding_mismatch",
            "authority_scope": a.scope,
            "effect_scope": inputs.scope,
        }
    if a.effective_expires_at is None:
        # No issuer expiry and no policy max_age derivable ⇒ deny (§2.2).
        return {"cause": "no_expiry_derivable", "authority_ref": a.authority_ref}
    if inputs.now > a.effective_expires_at:
        return {
            "cause": "expired",
            "authority_ref": a.authority_ref,
            "expired_at": a.effective_expires_at.isoformat(),
            "gate_time": inputs.now.isoformat(),
        }
    return None


def _branch_check(inputs: GateInputs) -> dict[str, Any] | None:
    if inputs.branch_ref is not None and inputs.branch_cancelled:
        return {"cause": "branch_cancelled", "branch_ref": inputs.branch_ref}
    return None


def _dedup_check(inputs: GateInputs) -> dict[str, Any] | None:
    blocking = [
        e
        for e in inputs.executions
        if e.frontier in DEDUP_BLOCKING_FRONTIERS
        and e.execution_id != inputs.waive_execution_id
    ]
    if not blocking:
        return None
    return {
        "cause": "duplicate_intent",
        "blocking_executions": [
            {
                "execution_id": e.execution_id,
                "step": e.step,
                "operation_id": e.operation_id,
                "frontier": e.frontier,
                "receipt_ids": list(e.receipt_ids),
                "finding_ids": list(e.finding_ids),
            }
            for e in blocking
        ],
        "parameter_variants": list(inputs.parameter_variants),
    }


def evaluate(inputs: GateInputs) -> GateDecision:
    """Run the four ordered checks; abort at the first deny; record every
    check's status (passed / denied / not_reached) plus input digests."""
    if inputs.variant not in GATE_VARIANTS:
        raise ValueError(f"unknown gate variant {inputs.variant!r}")

    check_fns = {
        "deny_list": _deny_list_check,
        "authority": _authority_check,
        "branch_lineage": _branch_check,
        "dedup": _dedup_check,
    }
    input_digest = canonical_digest(
        {
            "effect_id": inputs.effect_id,
            "variant": inputs.variant,
            "gate_time": inputs.now.isoformat(),
            "deny_entries": [d.deny_id for d in inputs.deny_entries],
            "authority": inputs.authority.authority_id if inputs.authority else None,
            "branch_cancelled": inputs.branch_cancelled,
            "frontiers": {str(e.execution_id): e.frontier for e in inputs.executions},
        }
    )

    checks: list[dict[str, Any]] = []
    deny_check: str | None = None
    deny_evidence: dict[str, Any] = {}
    for name in GATE_CHECKS:
        if deny_check is not None:
            checks.append({"check": name, "status": "not_reached"})
            continue
        result = check_fns[name](inputs)
        if result is None:
            checks.append({"check": name, "status": "passed"})
        else:
            checks.append({"check": name, "status": "denied", "evidence": result})
            deny_check = name
            deny_evidence = result

    evidence: dict[str, Any] = {"input_digest": input_digest}
    if deny_check is not None:
        evidence.update(deny_evidence)
        return GateDecision("DENY", deny_check, checks, evidence)
    return GateDecision("ALLOW", None, checks, evidence)
