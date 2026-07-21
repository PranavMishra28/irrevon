"""Reconciliation and calibrated absence (RFC-002 §6).

Adjudication per tier: C2 queries the destination's authoritative status in key
strength order (stamped client reference → receipt destination_ref → declared
queryable keys); C1 replays in-window via the claim discipline; C3 has NO
adjudication — park and escalate, only a human may settle. ABSENT is trusted
only under the confirmed-absence protocol (§6.2): key coverage + declared
settlement lag + two reads a re-read gap apart. Where the declaration's
``status_settlement_lag`` is null, a reconciled-absent settle is still
permitted, but the LOST finding is auto-routed ESCALATED_HUMAN and automatic
redispatch is FORBIDDEN — absence without a visibility bound supports human
judgment only.

``reconcile()`` adjudicates OPEN executions; on settled records it returns
recorded findings and issues NO destination query (§6.3). ``audit()`` is the
explicit second mode: new observations against settled records, append-only.
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from datetime import timedelta
from typing import Any

from detent.adapters.base import Adapter, StatusAnswer
from detent.errors import CapabilityUnsupported
from detent.ledger import Ledger
from detent.testhooks import syncpoint

__all__ = ["ReconcileConfig", "ReconcileReport", "audit_effect", "reconcile_effect"]

_DURATION_RE = re.compile(
    r"^PT(?:(?P<h>\d+)H)?(?:(?P<m>\d+)M)?(?:(?P<s>\d+(?:\.\d+)?)S)?$"
)


def parse_duration(value: str) -> timedelta:
    """Minimal ISO 8601 duration parser for the declared consistency bounds."""
    match = _DURATION_RE.match(value)
    if not match or not any(match.groups()):
        if value == "PT0S":
            return timedelta(0)
        raise ValueError(f"unsupported ISO 8601 duration {value!r}")
    return timedelta(
        hours=int(match.group("h") or 0),
        minutes=int(match.group("m") or 0),
        seconds=float(match.group("s") or 0),
    )


@dataclass(frozen=True, slots=True)
class ReconcileConfig:
    """RFC-002 §13 tunables [DD] — defaults per the ratified table; tests may
    tighten the gaps, never the protocol."""

    stuck_threshold_s: float = 300.0
    absence_reread_gap_s: float = 60.0
    probe_deadline_s: float = 10.0


@dataclass(slots=True)
class ReconcileReport:
    queried: int = 0
    settled: list[dict[str, Any]] = field(default_factory=list)
    still_ambiguous: list[str] = field(default_factory=list)
    skipped_young: list[str] = field(default_factory=list)
    escalated: list[int] = field(default_factory=list)
    findings: list[int] = field(default_factory=list)


def _settlement_lag(declaration: dict[str, Any]) -> timedelta | None:
    raw = declaration["consistency"]["status_settlement_lag"]
    return None if raw is None else parse_duration(raw)


def reconcile_effect(
    ledger: Ledger,
    adapter: Adapter,
    effect_id: str,
    *,
    mode: str = "online",
    config: ReconcileConfig | None = None,
    actor: str | None = None,
) -> ReconcileReport:
    """Adjudicate the effect's open executions (§6.1). ``mode='recovery'`` has
    no age requirement and may close provably-abandoned open attempts with a
    LOST receipt; online reconcile may not."""
    config = config or ReconcileConfig()
    actor = actor or ("recovery" if mode == "recovery" else "reconciler")
    report = ReconcileReport()

    frontier = ledger.effect_frontier(effect_id)
    if frontier["frontier"] not in ("DISPATCHED", "AMBIGUOUS"):
        # Already settled: return recorded findings, no destination query (§6.3).
        report.findings = [f["finding_id"] for f in ledger.findings_for(effect_id)]
        return report

    execution = ledger.execution(frontier["execution_id"])
    report.queried += 1

    if frontier["frontier"] == "DISPATCHED":
        open_attempt = ledger.open_attempt(execution["execution_id"])
        if open_attempt is not None:
            if mode == "online":
                age_rows = ledger.query(
                    "SELECT EXTRACT(EPOCH FROM (now() - claimed_at)) AS age "
                    "FROM dispatch_attempts WHERE attempt_id = %s",
                    (open_attempt["attempt_id"],),
                )
                if float(age_rows[0]["age"]) < config.stuck_threshold_s:
                    # A live wire call may still land — skip (§6.1).
                    report.skipped_young.append(execution["operation_id"])
                    return report
                return _park_or_query(ledger, adapter, execution, report, config, actor)
            # Recovery mode: at boot every open attempt is provably abandoned,
            # so recovery closes it with a LOST receipt (§7.1) — freeing the slot.
            ledger.record_outcome(
                open_attempt["attempt_id"],
                "LOST",
                evidence={"recovery": "abandoned open attempt at boot"},
                recorded_by="recovery",
            )

    return _adjudicate_ambiguous(ledger, adapter, effect_id, report, config, actor)


def _park_or_query(
    ledger: Ledger,
    adapter: Adapter,
    execution: dict[str, Any],
    report: ReconcileReport,
    config: ReconcileConfig,
    actor: str,
) -> ReconcileReport:
    # Online, stuck-past-threshold DISPATCHED: the attempt row stays open (only
    # recovery may close it); adjudication would race the dispatcher. Park.
    report.still_ambiguous.append(execution["operation_id"])
    return report


def _adjudicate_ambiguous(
    ledger: Ledger,
    adapter: Adapter,
    effect_id: str,
    report: ReconcileReport,
    config: ReconcileConfig,
    actor: str,
) -> ReconcileReport:
    declaration = adapter.declare()
    tier = declaration["tier"]
    frontier = ledger.effect_frontier(effect_id)
    execution = ledger.execution(frontier["execution_id"])

    if tier == "C3":
        # No adjudication exists: park AMBIGUOUS; only a human may settle —
        # the impossibility boundary, demonstrated openly (§6.1).
        report.still_ambiguous.append(execution["operation_id"])
        report.escalated.append(execution["execution_id"])
        return report

    if tier == "C1" and declaration["idempotency"]["supported"]:
        return _c1_replay(ledger, adapter, execution, report, actor)

    return _c2_query(ledger, adapter, execution, report, config, actor)


def _record_probe(
    ledger: Ledger,
    adapter: Adapter,
    execution: dict[str, Any],
    answer: StatusAnswer,
    query_keys: dict[str, Any],
    probe_kind: str = "reconcile_open",
) -> int:
    return ledger.record_probe(
        execution["execution_id"],
        adapter.adapter_id,
        adapter.declaration_digest(),
        probe_kind,
        query_keys,
        answer.result,
        n_found=answer.n_found,
        destination_refs=answer.destination_refs,
        response_digest=answer.evidence.get("response_digest"),
    )


def _c2_query(
    ledger: Ledger,
    adapter: Adapter,
    execution: dict[str, Any],
    report: ReconcileReport,
    config: ReconcileConfig,
    actor: str,
) -> ReconcileReport:
    declaration = adapter.declare()
    # Key strength order (§6.1): k1 stamped client reference (operation_id in
    # the declaration's client_ref_field — always stamped at dispatch when the
    # field exists), k2 receipt destination_ref, k3 declared queryable keys.
    client_ref = (
        execution["operation_id"] if declaration["client_ref_field"] else None
    )
    receipt = ledger.latest_receipt(execution["execution_id"])
    destination_ref = receipt["destination_ref"] if receipt else None

    if client_ref is not None:
        answer = adapter.status_query(
            client_ref=client_ref, deadline_s=config.probe_deadline_s
        )
        query_keys: dict[str, Any] = {"client_ref": client_ref}
    elif destination_ref is not None:
        answer = adapter.status_query(
            destination_ref=destination_ref, deadline_s=config.probe_deadline_s
        )
        query_keys = {"destination_ref": destination_ref}
    else:
        # Key-coverage rule (§6.1): no covering key set — effectively C3 for
        # this record; no confirmed-absence is reachable. Park and escalate.
        report.still_ambiguous.append(execution["operation_id"])
        report.escalated.append(execution["execution_id"])
        return report

    probe_id = _record_probe(ledger, adapter, execution, answer, query_keys)
    syncpoint("reconcile.pre_settle")

    if answer.result == "PRESENT":
        assert answer.n_found is not None
        if answer.n_found == 1:
            _, finding_id = ledger.settle_ambiguous(
                execution["execution_id"],
                "SETTLED_COMMITTED",
                "reconciled_present",
                actor,
                {"probe_ids": [probe_id]},
                classification="CONFIRMED_UNIQUE",
                destination_ref=answer.destination_refs[0],
                created_by=actor,
            )
        else:
            # DUPLICATE keeps the canonical n>1 meaning (AM-18).
            _, finding_id = ledger.settle_ambiguous(
                execution["execution_id"],
                "SETTLED_COMMITTED",
                "reconciled_present",
                actor,
                {"probe_ids": [probe_id]},
                classification="DUPLICATE",
                excess_effect_count=answer.n_found - 1,
                destination_ref=answer.destination_refs[0],
                created_by=actor,
            )
        report.settled.append(
            {
                "effect_id": execution["effect_id"],
                "from": "AMBIGUOUS",
                "to": "SETTLED_COMMITTED",
            }
        )
        if finding_id is not None:
            report.findings.append(finding_id)
        return report

    if answer.result == "ABSENT":
        return _confirmed_absence(
            ledger, adapter, execution, report, config, actor, probe_id, query_keys
        )

    # INDETERMINATE: retry-with-backoff is the ops loop's job; park, surface.
    report.still_ambiguous.append(execution["operation_id"])
    return report


def _confirmed_absence(
    ledger: Ledger,
    adapter: Adapter,
    execution: dict[str, Any],
    report: ReconcileReport,
    config: ReconcileConfig,
    actor: str,
    first_probe_id: int,
    query_keys: dict[str, Any],
) -> ReconcileReport:
    """The §6.2 protocol: (1) key coverage held by construction of the caller;
    (2) settlement lag: probe time ≥ claim time + declared lag; (3) two reads
    ≥ re-read gap apart. A null declared lag still permits the settle but
    auto-routes ESCALATED_HUMAN and forbids automatic redispatch."""
    declaration = adapter.declare()
    lag = _settlement_lag(declaration)

    if lag is not None:
        rows = ledger.query(
            """
            SELECT EXTRACT(EPOCH FROM (now() - a.claimed_at)) AS since_claim
            FROM dispatch_attempts a WHERE a.execution_id = %s
            ORDER BY a.attempt_no DESC LIMIT 1
            """,
            (execution["execution_id"],),
        )
        if rows and float(rows[0]["since_claim"]) < lag.total_seconds():
            # Inside the declared visibility bound: absence is not yet
            # authoritative. Stay AMBIGUOUS.
            report.still_ambiguous.append(execution["operation_id"])
            return report

    # Two-read rule. The re-read gap is a tunable; the second probe must also
    # satisfy key coverage and the lag (same keys, later time).
    if config.absence_reread_gap_s > 0:
        import time

        time.sleep(config.absence_reread_gap_s)
    second = adapter.status_query(
        **query_keys, deadline_s=config.probe_deadline_s
    )
    second_probe_id = _record_probe(ledger, adapter, execution, second, query_keys)
    if second.result != "ABSENT":
        # The effect materialized between reads — adjudicate afresh next pass.
        report.still_ambiguous.append(execution["operation_id"])
        return report

    _, finding_id = ledger.settle_ambiguous(
        execution["execution_id"],
        "SETTLED_FAILED",
        "reconciled_absent",
        actor,
        {"probe_ids": [first_probe_id, second_probe_id]},
        classification="LOST",
        created_by=actor,
    )
    report.settled.append(
        {
            "effect_id": execution["effect_id"],
            "from": "AMBIGUOUS",
            "to": "SETTLED_FAILED",
        }
    )
    assert finding_id is not None
    report.findings.append(finding_id)

    if _settlement_lag(declaration) is None:
        # §6.2: no finite visibility bound ⇒ the LOST finding is auto-routed
        # ESCALATED_HUMAN; automatic redispatch is forbidden downstream.
        ledger.resolve_finding(
            finding_id,
            "OPEN",
            "ESCALATED_HUMAN",
            "system",
            {
                "note": "confirmed-absence without a declared settlement lag "
                "supports human judgment only (RFC-002 §6.2)"
            },
        )
        report.escalated.append(finding_id)
    return report


def _c1_replay(
    ledger: Ledger,
    adapter: Adapter,
    execution: dict[str, Any],
    report: ReconcileReport,
    actor: str,
) -> ReconcileReport:
    """§5.3 item 2: in-window replay probe reusing the SAME operation_id/key —
    the declaration guarantees replay-not-re-execution semantics."""
    from detent.adapters.base import DispatchOrder

    claim = ledger.claim_replay_probe(execution["execution_id"])
    record = ledger.effect_record(execution["effect_id"])
    assert claim.attempt_id is not None and claim.operation_id is not None
    result = adapter.dispatch(
        DispatchOrder(
            operation_id=claim.operation_id,
            effect_type=record["effect_type"],
            payload=dict(record["parameters"]),
            client_ref=claim.idempotency_key or claim.operation_id,
        ),
        deadline_s=10.0,
    )
    outcome = ledger.record_replay_outcome(
        claim.attempt_id,
        result.transport_outcome,
        actor=actor,
        destination_ref=result.destination_ref,
        response_digest=result.response_digest,
        evidence={**result.evidence, "replay_probe": True},
    )
    if outcome.settled:
        report.settled.append(
            {
                "effect_id": execution["effect_id"],
                "from": "AMBIGUOUS",
                "to": outcome.lifecycle,
            }
        )
        if outcome.lifecycle == "SETTLED_COMMITTED":
            finding_id = ledger.attach_finding(
                execution["effect_id"],
                adapter.adapter_id,
                "CONFIRMED_UNIQUE",
                {"receipt_id": outcome.receipt_id, "replay_probe": True},
                destination_ref=result.destination_ref,
                created_by=actor if actor in ("reconciler", "recovery") else "human",
            )
            report.findings.append(finding_id)
    else:
        report.still_ambiguous.append(execution["operation_id"])
    return report


def audit_effect(
    ledger: Ledger,
    adapter: Adapter,
    effect_id: str,
    *,
    config: ReconcileConfig | None = None,
) -> ReconcileReport:
    """§6.3 audit mode: new destination observations against a SETTLED record,
    append-only, producing DUPLICATE / CONTRADICTED findings per §3.2 without
    rewriting prior facts."""
    config = config or ReconcileConfig()
    report = ReconcileReport()
    frontier = ledger.effect_frontier(effect_id)
    if frontier["frontier"] not in ("SETTLED_COMMITTED", "SETTLED_FAILED"):
        raise CapabilityUnsupported(
            "audit applies to settled records; use reconcile for open ones (§6.3)"
        )
    execution = ledger.execution(frontier["execution_id"])
    declaration = adapter.declare()
    if declaration["tier"] == "C3" or not declaration["queryable"]["supported"]:
        raise CapabilityUnsupported("audit needs a queryable destination")

    answer = adapter.status_query(
        client_ref=execution["operation_id"], deadline_s=config.probe_deadline_s
    )
    probe_id = _record_probe(
        ledger, adapter, execution, answer,
        {"client_ref": execution["operation_id"]}, probe_kind="audit",
    )
    report.queried = 1

    settle_evidence = ledger.query(
        """
        SELECT transition_seq, evidence FROM effect_transitions
        WHERE execution_id = %s AND to_state = %s
        ORDER BY transition_seq DESC LIMIT 1
        """,
        (execution["execution_id"], frontier["frontier"]),
    )

    if frontier["frontier"] == "SETTLED_COMMITTED":
        if answer.result == "PRESENT" and (answer.n_found or 0) > 1:
            existing = {
                f["classification"] for f in ledger.findings_for(effect_id)
            }
            if "DUPLICATE" not in existing:
                finding_id = ledger.attach_finding(
                    effect_id,
                    adapter.adapter_id,
                    "DUPLICATE",
                    {"probe_ids": [probe_id], "audit": True},
                    excess_effect_count=(answer.n_found or 1) - 1,
                    destination_ref=answer.destination_refs[0],
                    created_by="reconciler",
                )
                report.findings.append(finding_id)
        elif answer.result == "ABSENT":
            # Committed-then-vanished: prior commit evidence + fresh absence.
            finding_id = ledger.attach_finding(
                effect_id,
                adapter.adapter_id,
                "CONTRADICTED",
                {
                    "probe_ids": [probe_id],
                    "settle_transition_seq": settle_evidence[0]["transition_seq"]
                    if settle_evidence
                    else None,
                    "direction": "committed_then_vanished",
                },
                created_by="reconciler",
            )
            report.findings.append(finding_id)
    else:  # SETTLED_FAILED
        if answer.result == "PRESENT":
            # False-failure / unrecorded commit — the C3' contradictory path.
            finding_id = ledger.attach_finding(
                effect_id,
                adapter.adapter_id,
                "CONTRADICTED",
                {
                    "probe_ids": [probe_id],
                    "settle_transition_seq": settle_evidence[0]["transition_seq"]
                    if settle_evidence
                    else None,
                    "direction": "failed_but_present",
                },
                destination_ref=answer.destination_refs[0],
                created_by="reconciler",
            )
            report.findings.append(finding_id)
    return report
