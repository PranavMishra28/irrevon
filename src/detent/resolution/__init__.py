"""Resolution operations (RFC-002 §3.3, §5.3 item 3, §7.3).

``resolve(finding, action, evidence)`` executes a dimension-C action with the
engine-level preconditions the locked ledger function cannot see:

- REDISPATCHED (LOST findings only — the table enforces the rest): requires
  confirmed-absence evidence younger than the redispatch bound (else a fresh
  probe inside the flow), fresh authority, and the full gate on the NEW
  execution. The ``policy_auto`` variant additionally requires a finite
  declared ``status_settlement_lag`` and per-effect-type opt-in.
- COMPENSATED: requires a REGISTERED compensating intent — distinct
  effect_type, same stable-id core plus ``compensates_finding_id`` as an
  additional stable id (keeps compensation identity re-synthesis-proof, §7.3).
  CLOSED only when the compensating effect settles COMMITTED.
- ACCEPTED_AS_IS closes in the same transaction. ESCALATED_HUMAN parks.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from detent.adapters.base import Adapter
from detent.dispatcher import dispatch
from detent.errors import ResolutionInvalid
from detent.ledger import Ledger
from detent.reconciler import ReconcileConfig

__all__ = ["ResolutionConfig", "resolve"]


@dataclass(frozen=True, slots=True)
class ResolutionConfig:
    redispatch_evidence_bound_s: float = 600.0  # §13 tunable [DD]
    auto_redispatch_effect_types: frozenset[str] = field(default_factory=frozenset)
    reconcile: ReconcileConfig = field(default_factory=ReconcileConfig)


def resolve(
    ledger: Ledger,
    adapters: dict[str, Adapter],
    finding_id: int,
    action: str,
    evidence: dict[str, Any],
    *,
    actor: str = "human",
    config: ResolutionConfig | None = None,
) -> dict[str, Any]:
    from detent.errors import reject_advisory

    reject_advisory(evidence, "resolve")
    config = config or ResolutionConfig()
    rows = ledger.query(
        "SELECT * FROM findings WHERE finding_id = %s", (finding_id,)
    )
    if not rows:
        raise ResolutionInvalid(f"no finding {finding_id}")
    finding = rows[0]
    current_rows = ledger.query(
        "SELECT to_status FROM finding_resolutions WHERE finding_id = %s "
        "ORDER BY resolution_seq DESC LIMIT 1",
        (finding_id,),
    )
    current = current_rows[0]["to_status"] if current_rows else "OPEN"

    if action == "ACCEPTED_AS_IS":
        # Same-transaction close (§3.3).
        ledger.resolve_chain(
            finding_id,
            [(current, "ACCEPTED_AS_IS"), ("ACCEPTED_AS_IS", "CLOSED")],
            actor,
            evidence,
        )
        return {"finding_id": finding_id, "status": "CLOSED"}

    if action == "ESCALATED_HUMAN":
        ledger.resolve_finding(finding_id, current, "ESCALATED_HUMAN", actor, evidence)
        return {"finding_id": finding_id, "status": "ESCALATED_HUMAN"}

    if action == "COMPENSATED":
        return _compensate(ledger, finding, current, evidence, actor)

    if action == "REDISPATCHED":
        return _redispatch(
            ledger, adapters, finding, current, evidence, actor, config
        )

    raise ResolutionInvalid(f"unknown resolution action {action!r}")


def _compensate(
    ledger: Ledger,
    finding: dict[str, Any],
    current: str,
    evidence: dict[str, Any],
    actor: str,
) -> dict[str, Any]:
    comp_effect_id = evidence.get("compensating_effect_id")
    if not comp_effect_id:
        raise ResolutionInvalid(
            "COMPENSATED requires evidence.compensating_effect_id of a "
            "registered compensating intent (§7.3)"
        )
    record = ledger.effect_record(str(comp_effect_id))
    stable_ids = dict(record["stable_ids"])
    if stable_ids.get("compensates_finding_id") != str(finding["finding_id"]):
        raise ResolutionInvalid(
            "the compensating intent must carry compensates_finding_id="
            f"{finding['finding_id']} in its stable ids (re-synthesis-proof "
            "compensation identity, §7.3)"
        )
    ledger.resolve_finding(
        finding["finding_id"], current, "COMPENSATED", actor,
        {**evidence, "compensating_effect_id": comp_effect_id},
    )
    # CLOSED only when the compensating effect settles COMMITTED (§3.3).
    frontier = ledger.effect_frontier(str(comp_effect_id))
    if frontier["frontier"] == "SETTLED_COMMITTED":
        ledger.resolve_finding(
            finding["finding_id"], "COMPENSATED", "CLOSED", "system",
            {"compensating_effect_settled": True},
        )
        return {"finding_id": finding["finding_id"], "status": "CLOSED"}
    return {"finding_id": finding["finding_id"], "status": "COMPENSATED"}


def _redispatch(
    ledger: Ledger,
    adapters: dict[str, Adapter],
    finding: dict[str, Any],
    current: str,
    evidence: dict[str, Any],
    actor: str,
    config: ResolutionConfig,
) -> dict[str, Any]:
    effect_id = finding["effect_id"]
    if effect_id is None:
        raise ResolutionInvalid("REDISPATCHED needs a ledger-keyed finding")
    record = ledger.effect_record(effect_id)
    adapter = adapters[record["adapter_id"]]
    declaration = adapter.declare()

    if actor == "policy_auto":
        # §5.3-3: opt-in, never default; and never without a finite bound.
        if declaration["consistency"]["status_settlement_lag"] is None:
            raise ResolutionInvalid(
                "automatic redispatch is forbidden when the declaration has no "
                "finite status_settlement_lag (RFC-002 §6.2)"
            )
        if record["effect_type"] not in config.auto_redispatch_effect_types:
            raise ResolutionInvalid(
                f"effect type {record['effect_type']!r} has not opted in to "
                "automatic redispatch-on-absence (RFC-002 §5.3)"
            )

    fresh_ref = evidence.get("fresh_authority_ref")
    stamped_at = evidence.get("stamped_at")
    if not fresh_ref or not stamped_at:
        raise ResolutionInvalid(
            "REDISPATCHED requires fresh authority evidence "
            "(fresh_authority_ref + stamped_at)"
        )

    # Confirmed-absence evidence younger than the redispatch bound, else a
    # fresh probe inside the flow (§5.3-3).
    frontier = ledger.effect_frontier(effect_id)
    age_rows = ledger.query(
        """
        SELECT EXTRACT(EPOCH FROM (now() - MAX(p.recorded_at))) AS age
        FROM status_probes p
        WHERE p.execution_id = %s AND p.result = 'ABSENT'
        """,
        (frontier["execution_id"],),
    )
    age = age_rows[0]["age"] if age_rows and age_rows[0]["age"] is not None else None
    if age is None or float(age) > config.redispatch_evidence_bound_s:
        fresh = adapter.status_query(
            client_ref=frontier["operation_id"],
            deadline_s=config.reconcile.probe_deadline_s,
        )
        if fresh.result != "ABSENT":
            raise ResolutionInvalid(
                "fresh probe did not confirm absence; redispatch would risk a "
                "duplicate (never re-dispatch on belief, master doc §7.4)"
            )
        ledger.record_probe(
            frontier["execution_id"],
            adapter.adapter_id,
            adapter.declaration_digest(),
            "reconcile_open",
            {"client_ref": frontier["operation_id"]},
            fresh.result,
            n_found=fresh.n_found,
        )

    ledger.resolve_finding(
        finding["finding_id"], current, "REDISPATCHED", actor, evidence
    )
    ledger.append_authority(effect_id, str(fresh_ref), str(stamped_at))
    opened = ledger.open_execution(effect_id, "resolve_redispatch")
    report = dispatch(
        ledger, adapter, effect_id, variant="resolve_redispatch", kind="primary"
    )
    result: dict[str, Any] = {
        "finding_id": finding["finding_id"],
        "status": "REDISPATCHED",
        "replacement_operation_id": opened["operation_id"],
        "dispatch_outcome": report.outcome,
        "lifecycle": report.lifecycle,
    }
    # CLOSED only when the replacement settles COMMITTED (§3.3); otherwise the
    # finding stays visibly un-CLOSED in the ops queue.
    if report.lifecycle == "SETTLED_COMMITTED":
        ledger.resolve_finding(
            finding["finding_id"], "REDISPATCHED", "CLOSED", "system",
            {"replacement_operation_id": opened["operation_id"]},
        )
        result["status"] = "CLOSED"
    return result
