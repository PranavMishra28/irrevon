"""The Effect Ledger — the only module with SQL; owns transactions (RFC-002 §14).

Implements the registrar write path (RFC-002 §1), the claim protocol (§5.1),
the dispatch outcome map's ledger half (§5.2), settle-with-finding, and typed
wrappers over the locked §2.3 functions. Locks are held only inside short claim
transactions and NEVER across wire I/O; the wire call happens strictly after
the claim transaction commits.

Lock order everywhere: ``scope_slots`` → ``effect_records`` → ``findings``
(§5.1). READ COMMITTED isolation; correctness is carried by the locked
functions, unique arbiters, and durable claims.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from typing import Any, Literal

import psycopg
from psycopg.types.json import Jsonb

from irrevon import SCHEMA_VERSION
from irrevon.contract import (
    IntentContract,
    PersistedIdentity,
    adjudicate_reregistration,
    validate_intent_contract,
)
from irrevon.errors import IllegalState, NotFound, ScopeBusy, reject_advisory
from irrevon.gate import (
    AuthorityView,
    BlockingExecution,
    DenyEntryView,
    GateDecision,
    GateInputs,
    evaluate,
)
from irrevon.identity import (
    canonical_digest,
    derive_idempotency_key,
    derive_intent_id,
    identity_tuple_bytes,
)
from irrevon.ledger.db import connect, translated_errors
from irrevon.testhooks import crashpoint

__all__ = [
    "ClaimOutcome",
    "Ledger",
    "OutcomeRecord",
    "Registration",
]


@dataclass(frozen=True, slots=True)
class Registration:
    schema_version: str
    effect_id: str
    operation_id: str
    lifecycle: str
    replayed: bool
    parameter_variant_digest: str | None = None
    authority_refresh: bool = False


@dataclass(frozen=True, slots=True)
class ClaimOutcome:
    """Discriminated result of the claim transaction (RFC-002 §5.1/§5.2)."""

    outcome: Literal["claimed", "denied", "pending_reconciliation"]
    effect_id: str
    lifecycle: str
    # claimed:
    execution_id: int | None = None
    attempt_id: int | None = None
    attempt_no: int | None = None
    operation_id: str | None = None
    idempotency_key: str | None = None
    adapter_id: str | None = None
    # denied:
    decision_id: int | None = None
    deny_check: str | None = None
    deny_evidence: dict[str, Any] | None = None
    deny_subtype: str | None = None
    # pending_reconciliation:
    last_receipt: dict[str, Any] | None = None


@dataclass(frozen=True, slots=True)
class OutcomeRecord:
    """Result of the T-OUTCOME transaction (§5.1)."""

    settled: bool  # False when this outcome lost the race and landed late
    lifecycle: str
    receipt_id: int | None = None
    late_id: int | None = None
    contradicts_settle: bool = False


_SETTLE_MAP: dict[str, tuple[str, str]] = {
    "OK": ("SETTLED_COMMITTED", "receipt_ok"),
    "FAILED": ("SETTLED_FAILED", "receipt_failed"),
    "TIMEOUT": ("AMBIGUOUS", "receipt_timeout"),
    "LOST": ("AMBIGUOUS", "receipt_lost"),
}


class Ledger:
    """One connection, one writer. Concurrency tests open multiple instances."""

    def __init__(self, dsn: str) -> None:
        self._conn = connect(dsn)

    def close(self) -> None:
        self._conn.close()

    def __enter__(self) -> Ledger:
        return self

    def __exit__(self, *exc: object) -> None:
        self.close()

    # ── registerIntent (RFC-002 §1) ───────────────────────────────────────────

    def register_intent(
        self, raw: object, declaration_digest: str
    ) -> Registration:
        reject_advisory(raw, "registerIntent")
        contract = validate_intent_contract(raw)
        effect_id = derive_intent_id(
            contract.stable_ids, contract.effect_type, contract.scope
        )
        canonical = identity_tuple_bytes(
            contract.stable_ids, contract.effect_type, contract.scope
        )
        registration: Registration
        with self._conn.transaction(), translated_errors():
            inserted = self._conn.execute(
                """
                INSERT INTO effect_records (effect_id, effect_type, effect_class,
                  scope, stable_ids, adapter_id, declaration_digest, parameters,
                  parameters_digest, contract_canonical, branch_ref, event_time)
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                ON CONFLICT (effect_id) DO NOTHING
                RETURNING effect_id
                """,
                (
                    effect_id,
                    contract.effect_type,
                    contract.effect_class,
                    contract.scope,
                    Jsonb(contract.stable_ids),
                    contract.adapter_id,
                    declaration_digest,
                    Jsonb(contract.parameters.reveal_for_adapter()),
                    contract.parameters_digest,
                    canonical,
                    contract.branch_ref,
                    contract.event_time,
                ),
            ).fetchone()
            if inserted is not None:
                self._append_authority(effect_id, contract)
                row = self._conn.execute(
                    "SELECT * FROM ledger_open_execution(%s, 'register')",
                    (effect_id,),
                ).fetchone()
                assert row is not None
                registration = Registration(
                    schema_version=SCHEMA_VERSION,
                    effect_id=effect_id,
                    operation_id=row["operation_id"],
                    lifecycle=row["state"],
                    replayed=False,
                )
                # Seam: INSERTs prepared, COMMIT not yet issued — a SIGKILL here
                # must be provably effect-free (kill-before-persist, §12.1 row 2).
                crashpoint("persist.pre_commit")
            else:
                # Loser of a concurrent register (or an intentional replay):
                # re-read the winner's committed row and adjudicate (§1 table).
                stored = self._persisted_identity(effect_id)
                decision = adjudicate_reregistration(stored, contract)
                if decision.parameter_variant_digest is not None:
                    self._conn.execute(
                        """
                        INSERT INTO parameter_variants (effect_id, parameters_digest, event_time)
                        VALUES (%s, %s, %s)
                        """,
                        (effect_id, decision.parameter_variant_digest, contract.event_time),
                    )
                if decision.authority_refresh:
                    self._append_authority(effect_id, contract)
                frontier = self._latest_frontier(effect_id)
                assert frontier is not None
                registration = Registration(
                    schema_version=SCHEMA_VERSION,
                    effect_id=effect_id,
                    operation_id=frontier["operation_id"],
                    lifecycle=frontier["frontier"],
                    replayed=True,
                    parameter_variant_digest=decision.parameter_variant_digest,
                    authority_refresh=decision.authority_refresh,
                )
        # Seam: after COMMIT, before returning effect_id.
        crashpoint("persist.post_commit")
        return registration

    def _append_authority(self, effect_id: str, contract: IntentContract) -> None:
        row = self._conn.execute(
            """
            INSERT INTO authorities (authority_ref, scope, stamped_at)
            VALUES (%s, %s, %s) RETURNING authority_id
            """,
            (contract.authority_ref, contract.scope, contract.stamped_at),
        ).fetchone()
        assert row is not None
        self._conn.execute(
            "INSERT INTO effect_authorities (effect_id, authority_id) VALUES (%s, %s)",
            (effect_id, row["authority_id"]),
        )

    def _persisted_identity(self, effect_id: str) -> PersistedIdentity:
        record = self._conn.execute(
            "SELECT * FROM effect_records WHERE effect_id = %s", (effect_id,)
        ).fetchone()
        if record is None:
            raise NotFound(f"no effect record {effect_id}")
        authority = self._conn.execute(
            """
            SELECT a.authority_ref, a.stamped_at
            FROM effect_authorities ea JOIN authorities a USING (authority_id)
            WHERE ea.effect_id = %s ORDER BY ea.link_id DESC LIMIT 1
            """,
            (effect_id,),
        ).fetchone()
        assert authority is not None
        return PersistedIdentity(
            effect_id=effect_id,
            effect_class=record["effect_class"],
            adapter_id=record["adapter_id"],
            branch_ref=record["branch_ref"],
            authority_ref=authority["authority_ref"],
            stamped_at=authority["stamped_at"].isoformat().replace("+00:00", "Z"),
            parameters_digest=record["parameters_digest"],
            event_time=(
                record["event_time"].isoformat().replace("+00:00", "Z")
                if record["event_time"] is not None
                else None
            ),
        )

    # ── Claim protocol (RFC-002 §5.1) + dispatch outcome map (§5.2) ───────────

    def claim_dispatch(
        self,
        effect_id: str,
        *,
        variant: str = "dispatch",
        kind: str = "primary",
        request_digest: str | None = None,
        waive_execution_id: int | None = None,
    ) -> ClaimOutcome:
        """T-CLAIM: one transaction; on ALLOW the caller performs the wire call
        strictly AFTER this method returns (no transaction open, no lock held)."""
        with self._conn.transaction(), translated_errors():
            record = self._conn.execute(
                "SELECT * FROM effect_records WHERE effect_id = %s", (effect_id,)
            ).fetchone()
            if record is None:
                raise NotFound(f"no effect record {effect_id}")

            # Lock order: scope_slots → effect_records (§5.1).
            self._conn.execute(
                """
                INSERT INTO scope_slots (scope, effect_type) VALUES (%s, %s)
                ON CONFLICT DO NOTHING
                """,
                (record["scope"], record["effect_type"]),
            )
            self._conn.execute(
                "SELECT 1 FROM scope_slots WHERE scope = %s AND effect_type = %s FOR UPDATE",
                (record["scope"], record["effect_type"]),
            )
            self._conn.execute(
                "SELECT 1 FROM effect_records WHERE effect_id = %s FOR UPDATE",
                (effect_id,),
            )

            frontier = self._latest_frontier(effect_id)
            if frontier is None:
                raise IllegalState(f"effect {effect_id} has no execution")
            lifecycle: str = frontier["frontier"]

            if lifecycle == "CANCELLED":
                raise IllegalState(
                    f"effect {effect_id} is CANCELLED; dispatch is illegal (§5.2)"
                )
            if lifecycle in ("DISPATCHED", "AMBIGUOUS"):
                # Never re-dispatch on belief (§5.2); no wire call, no gate run.
                return ClaimOutcome(
                    outcome="pending_reconciliation",
                    effect_id=effect_id,
                    lifecycle=lifecycle,
                    operation_id=frontier["operation_id"],
                    last_receipt=self._last_receipt(frontier["execution_id"]),
                )

            # Open-attempt check on the slot (slot_busy, retryable — §5.1).
            busy = self._conn.execute(
                """
                SELECT attempt_id, effect_id FROM open_attempts
                WHERE scope = %s AND effect_type = %s LIMIT 1
                """,
                (record["scope"], record["effect_type"]),
            ).fetchone()
            if busy is not None:
                raise ScopeBusy(
                    "an open attempt exists in this (scope, effect_type) slot",
                    details={
                        "attempt_id": busy["attempt_id"],
                        "blocking_effect_id": busy["effect_id"],
                    },
                )

            inputs = self._gate_inputs(record, variant, waive_execution_id)
            decision = evaluate(inputs)
            if lifecycle == "SETTLED_FAILED" and decision.outcome == "ALLOW":
                # §5.2: settled-failed dispatch is an evidenced dedup deny with
                # subtype retryable_failed pointing at the explicit retry
                # operation — never a silent replay or implicit new attempt.
                decision = GateDecision(
                    "DENY",
                    "dedup",
                    decision.checks,
                    {
                        **decision.evidence,
                        "cause": "retryable_failed",
                        "settled_execution_id": frontier["execution_id"],
                        "retry_operation": "open_retry_execution",
                    },
                )
            decision_id = self._record_decision(
                effect_id, frontier["execution_id"], variant, decision
            )

            if decision.outcome == "DENY":
                subtype = None
                if decision.deny_check == "dedup" and lifecycle == "SETTLED_FAILED":
                    subtype = "retryable_failed"
                return ClaimOutcome(
                    outcome="denied",
                    effect_id=effect_id,
                    lifecycle=lifecycle,
                    decision_id=decision_id,
                    deny_check=decision.deny_check,
                    deny_evidence=decision.evidence,
                    deny_subtype=subtype,
                )

            # ALLOW on PERSISTED: claim the attempt + transition, atomically.
            execution_id: int = frontier["execution_id"]
            operation_id: str = frontier["operation_id"]
            key = derive_idempotency_key(operation_id)
            attempt_no_row = self._conn.execute(
                "SELECT COALESCE(MAX(attempt_no), 0) + 1 AS n FROM dispatch_attempts "
                "WHERE execution_id = %s",
                (execution_id,),
            ).fetchone()
            assert attempt_no_row is not None
            attempt_row = self._conn.execute(
                """
                INSERT INTO dispatch_attempts (execution_id, attempt_no, kind,
                  adapter_id, declaration_digest, idempotency_key, request_digest,
                  gate_decision_id)
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
                RETURNING attempt_id, attempt_no
                """,
                (
                    execution_id,
                    attempt_no_row["n"],
                    kind,
                    record["adapter_id"],
                    record["declaration_digest"],
                    key,
                    request_digest
                    or canonical_digest({"operation_id": operation_id}),
                    decision_id,
                ),
            ).fetchone()
            assert attempt_row is not None
            self._conn.execute(
                "SELECT ledger_transition(%s, 'PERSISTED', 'DISPATCHED', 'gate_allow', 'gate', %s)",
                (
                    execution_id,
                    Jsonb(
                        {
                            "decision_id": decision_id,
                            "attempt_id": attempt_row["attempt_id"],
                        }
                    ),
                ),
            )
            return ClaimOutcome(
                outcome="claimed",
                effect_id=effect_id,
                lifecycle="DISPATCHED",
                execution_id=execution_id,
                attempt_id=attempt_row["attempt_id"],
                attempt_no=attempt_row["attempt_no"],
                operation_id=operation_id,
                idempotency_key=key,
                adapter_id=record["adapter_id"],
            )

    def _gate_inputs(
        self,
        record: dict[str, Any],
        variant: str,
        waive_execution_id: int | None,
    ) -> GateInputs:
        effect_id: str = record["effect_id"]
        now_row = self._conn.execute("SELECT now() AS now").fetchone()
        assert now_row is not None
        now: datetime = now_row["now"]

        deny_rows = self._conn.execute(
            """
            SELECT d.deny_id, d.effect_class, d.effect_type, d.scope, d.reason
            FROM deny_entries d
            LEFT JOIN deny_lifts l ON l.deny_id = d.deny_id
            WHERE l.deny_id IS NULL
              AND (d.effect_class IS NULL OR d.effect_class = %s)
              AND (d.effect_type IS NULL OR d.effect_type = %s)
              AND (d.scope IS NULL OR d.scope = %s)
            ORDER BY d.deny_id
            """,
            (record["effect_class"], record["effect_type"], record["scope"]),
        ).fetchall()

        authority_row = self._conn.execute(
            """
            SELECT a.authority_id, a.authority_ref, a.scope, a.stamped_at,
                   COALESCE(a.expires_at, a.stamped_at + p.max_age) AS effective_expires_at
            FROM effect_authorities ea
            JOIN authorities a USING (authority_id)
            LEFT JOIN LATERAL (
              SELECT max_age FROM authority_policies
              WHERE scope_pattern IN (a.scope, '*')
              ORDER BY (scope_pattern = a.scope) DESC, policy_id DESC LIMIT 1
            ) p ON true
            WHERE ea.effect_id = %s
            ORDER BY ea.link_id DESC LIMIT 1
            """,
            (effect_id,),
        ).fetchone()

        branch_cancelled = False
        if record["branch_ref"] is not None:
            branch_cancelled = (
                self._conn.execute(
                    "SELECT 1 FROM branch_cancellations WHERE branch_ref = %s",
                    (record["branch_ref"],),
                ).fetchone()
                is not None
            )

        execution_rows = self._conn.execute(
            """
            SELECT f.execution_id, f.step, f.operation_id, f.frontier
            FROM execution_frontiers f WHERE f.effect_id = %s ORDER BY f.step
            """,
            (effect_id,),
        ).fetchall()
        executions = []
        for e in execution_rows:
            receipts = self._conn.execute(
                """
                SELECT r.receipt_id FROM dispatch_receipts r
                JOIN dispatch_attempts a USING (attempt_id)
                WHERE a.execution_id = %s ORDER BY r.receipt_id
                """,
                (e["execution_id"],),
            ).fetchall()
            executions.append(
                BlockingExecution(
                    execution_id=e["execution_id"],
                    step=e["step"],
                    operation_id=e["operation_id"],
                    frontier=e["frontier"],
                    receipt_ids=tuple(r["receipt_id"] for r in receipts),
                    finding_ids=tuple(
                        f["finding_id"]
                        for f in self._conn.execute(
                            "SELECT finding_id FROM findings WHERE effect_id = %s "
                            "ORDER BY finding_id",
                            (effect_id,),
                        ).fetchall()
                    ),
                )
            )

        variants = tuple(
            v["parameters_digest"]
            for v in self._conn.execute(
                "SELECT parameters_digest FROM parameter_variants WHERE effect_id = %s "
                "ORDER BY variant_id",
                (effect_id,),
            ).fetchall()
        )

        return GateInputs(
            variant=variant,
            effect_id=effect_id,
            effect_class=record["effect_class"],
            effect_type=record["effect_type"],
            scope=record["scope"],
            branch_ref=record["branch_ref"],
            now=now,
            deny_entries=tuple(
                DenyEntryView(
                    deny_id=d["deny_id"],
                    effect_class=d["effect_class"],
                    effect_type=d["effect_type"],
                    scope=d["scope"],
                    reason=d["reason"],
                )
                for d in deny_rows
            ),
            authority=(
                AuthorityView(
                    authority_id=authority_row["authority_id"],
                    authority_ref=authority_row["authority_ref"],
                    scope=authority_row["scope"],
                    stamped_at=authority_row["stamped_at"],
                    effective_expires_at=authority_row["effective_expires_at"],
                )
                if authority_row is not None
                else None
            ),
            branch_cancelled=branch_cancelled,
            executions=tuple(executions),
            parameter_variants=variants,
            waive_execution_id=waive_execution_id,
        )

    def _record_decision(
        self,
        effect_id: str,
        execution_id: int | None,
        variant: str,
        decision: GateDecision,
    ) -> int:
        row = self._conn.execute(
            """
            INSERT INTO gate_decisions (effect_id, execution_id, variant, outcome,
              deny_check, checks, evidence)
            VALUES (%s, %s, %s, %s, %s, %s, %s)
            RETURNING decision_id
            """,
            (
                effect_id,
                execution_id,
                variant,
                decision.outcome,
                decision.deny_check,
                Jsonb(decision.checks),
                Jsonb(decision.evidence),
            ),
        ).fetchone()
        assert row is not None
        return int(row["decision_id"])

    # ── T-OUTCOME (§5.1) ──────────────────────────────────────────────────────

    def record_outcome(
        self,
        attempt_id: int,
        transport_outcome: str,
        *,
        failure_kind: str | None = None,
        destination_ref: str | None = None,
        response_digest: str | None = None,
        evidence: dict[str, Any] | None = None,
        recorded_by: str = "dispatcher",
    ) -> OutcomeRecord:
        """Insert receipt + settle/AMBIGUOUS transition atomically. A late or
        losing outcome (another actor settled first) lands in late_responses; a
        contradiction additionally flags an audit reconcile (§5.1)."""
        if transport_outcome not in _SETTLE_MAP:
            raise IllegalState(
                f"unknown transport outcome {transport_outcome!r}: the closed set "
                "is OK|FAILED|TIMEOUT|LOST (RFC-002 §10)"
            )
        to_state, cause = _SETTLE_MAP[transport_outcome]
        actor = "recovery" if recorded_by == "recovery" else "dispatcher"
        evidence = evidence or {}
        crashpoint("receipt.pre_commit")
        result = self._record_outcome_txn(
            attempt_id, transport_outcome, to_state, cause, actor,
            failure_kind, destination_ref, response_digest, evidence, recorded_by,
        )
        # Seam: after the receipt/settle COMMIT (testing.md §3.3).
        crashpoint("receipt.post_commit")
        return result

    def _record_outcome_txn(
        self,
        attempt_id: int,
        transport_outcome: str,
        to_state: str,
        cause: str,
        actor: str,
        failure_kind: str | None,
        destination_ref: str | None,
        response_digest: str | None,
        evidence: dict[str, Any],
        recorded_by: str,
    ) -> OutcomeRecord:
        with self._conn.transaction(), translated_errors():
            attempt = self._conn.execute(
                """
                SELECT a.attempt_id, a.execution_id FROM dispatch_attempts a
                WHERE a.attempt_id = %s
                """,
                (attempt_id,),
            ).fetchone()
            if attempt is None:
                raise NotFound(f"no attempt {attempt_id}")
            execution_id: int = attempt["execution_id"]
            try:
                with self._conn.transaction():  # savepoint: receipt + transition
                    receipt = self._conn.execute(
                        """
                        INSERT INTO dispatch_receipts (attempt_id, transport_outcome,
                          failure_kind, destination_ref, response_digest, evidence,
                          recorded_by)
                        VALUES (%s, %s, %s, %s, %s, %s, %s)
                        RETURNING receipt_id
                        """,
                        (
                            attempt_id,
                            transport_outcome,
                            failure_kind,
                            destination_ref,
                            response_digest,
                            Jsonb(
                                {**evidence, "evidence_digest": canonical_digest(evidence)}
                            ),
                            recorded_by,
                        ),
                    ).fetchone()
                    assert receipt is not None
                    self._conn.execute(
                        "SELECT ledger_transition(%s, 'DISPATCHED', %s, %s, %s, %s)",
                        (
                            execution_id,
                            to_state,
                            cause,
                            actor,
                            Jsonb(
                                {"receipt_id": receipt["receipt_id"]}
                            ),
                        ),
                    )
                    return OutcomeRecord(
                        settled=True,
                        lifecycle=to_state,
                        receipt_id=receipt["receipt_id"],
                    )
            except psycopg.Error as err:
                # Lost the settle race (or a receipt already exists): the losing
                # outcome is recorded as a late response, never dropped (§5.1).
                if err.sqlstate not in ("23505", "DT001", "DT002"):
                    raise
                frontier_row = self._conn.execute(
                    """
                    SELECT frontier FROM execution_frontiers WHERE execution_id = %s
                    """,
                    (execution_id,),
                ).fetchone()
                settled_state = frontier_row["frontier"] if frontier_row else None
                contradicts = (
                    settled_state == "SETTLED_FAILED" and transport_outcome == "OK"
                ) or (
                    settled_state == "SETTLED_COMMITTED"
                    and transport_outcome == "FAILED"
                )
                late = self._conn.execute(
                    """
                    INSERT INTO late_responses (attempt_id, transport_outcome,
                      destination_ref, response_digest, evidence, contradicts_settle)
                    VALUES (%s, %s, %s, %s, %s, %s)
                    RETURNING late_id
                    """,
                    (
                        attempt_id,
                        transport_outcome,
                        destination_ref,
                        response_digest,
                        Jsonb(evidence),
                        contradicts,
                    ),
                ).fetchone()
                assert late is not None
                return OutcomeRecord(
                    settled=False,
                    lifecycle=settled_state or "UNKNOWN",
                    late_id=late["late_id"],
                    contradicts_settle=contradicts,
                )

    # ── Settle-with-finding (classify-and-settle is atomic, §3.2) ─────────────

    def settle_ambiguous(
        self,
        execution_id: int,
        to_state: str,
        cause: str,
        actor: str,
        evidence: dict[str, Any],
        *,
        classification: str | None = None,
        finding_evidence: dict[str, Any] | None = None,
        excess_effect_count: int | None = None,
        destination_ref: str | None = None,
        created_by: str | None = None,
    ) -> tuple[int, int | None]:
        """AMBIGUOUS→settled transition plus (optionally) the finding, in ONE
        transaction. Returns (transition_seq, finding_id | None)."""
        reject_advisory(evidence, "settle")
        crashpoint("settle.pre_commit")
        with self._conn.transaction(), translated_errors():
            exec_row = self._conn.execute(
                "SELECT effect_id FROM effect_executions WHERE execution_id = %s",
                (execution_id,),
            ).fetchone()
            if exec_row is None:
                raise NotFound(f"no execution {execution_id}")
            adapter_row = self._conn.execute(
                "SELECT adapter_id FROM effect_records WHERE effect_id = %s",
                (exec_row["effect_id"],),
            ).fetchone()
            assert adapter_row is not None
            seq_row = self._conn.execute(
                "SELECT ledger_transition(%s, 'AMBIGUOUS', %s, %s, %s, %s) AS seq",
                (
                    execution_id,
                    to_state,
                    cause,
                    actor,
                    Jsonb(evidence),
                ),
            ).fetchone()
            assert seq_row is not None
            finding_id: int | None = None
            if classification is not None:
                f_evidence = finding_evidence or evidence
                f_row = self._conn.execute(
                    "SELECT ledger_attach_finding(%s, %s, %s, %s, %s, %s, %s, %s) AS fid",
                    (
                        exec_row["effect_id"],
                        adapter_row["adapter_id"],
                        destination_ref,
                        classification,
                        excess_effect_count,
                        Jsonb(f_evidence),
                        canonical_digest(f_evidence),
                        created_by or actor,
                    ),
                ).fetchone()
                assert f_row is not None
                finding_id = f_row["fid"]
            return (seq_row["seq"], finding_id)

    # ── Locked-function wrappers ──────────────────────────────────────────────

    def transition(
        self,
        execution_id: int,
        expected_from: str | None,
        to_state: str,
        cause: str,
        actor: str,
        evidence: dict[str, Any],
    ) -> int:
        with self._conn.transaction(), translated_errors():
            row = self._conn.execute(
                "SELECT ledger_transition(%s, %s, %s, %s, %s, %s) AS seq",
                (
                    execution_id,
                    expected_from,
                    to_state,
                    cause,
                    actor,
                    Jsonb(evidence),
                ),
            ).fetchone()
            assert row is not None
            return int(row["seq"])

    def attach_finding(
        self,
        effect_id: str | None,
        adapter_id: str,
        classification: str,
        evidence: dict[str, Any],
        *,
        destination_ref: str | None = None,
        excess_effect_count: int | None = None,
        created_by: str = "reconciler",
    ) -> int:
        reject_advisory(evidence, "attach_finding")
        with self._conn.transaction(), translated_errors():
            row = self._conn.execute(
                "SELECT ledger_attach_finding(%s, %s, %s, %s, %s, %s, %s, %s) AS fid",
                (
                    effect_id,
                    adapter_id,
                    destination_ref,
                    classification,
                    excess_effect_count,
                    Jsonb(evidence),
                    canonical_digest(evidence),
                    created_by,
                ),
            ).fetchone()
            assert row is not None
            return int(row["fid"])

    def resolve_finding(
        self,
        finding_id: int,
        from_status: str,
        to_status: str,
        actor: str,
        evidence: dict[str, Any],
    ) -> int:
        reject_advisory(evidence, "resolve")
        with self._conn.transaction(), translated_errors():
            row = self._conn.execute(
                "SELECT ledger_resolve(%s, %s, %s, %s, %s) AS seq",
                (
                    finding_id,
                    from_status,
                    to_status,
                    actor,
                    Jsonb(evidence),
                ),
            ).fetchone()
            assert row is not None
            return int(row["seq"])

    def open_execution(self, effect_id: str, opened_by: str) -> dict[str, Any]:
        with self._conn.transaction(), translated_errors():
            row = self._conn.execute(
                "SELECT * FROM ledger_open_execution(%s, %s)",
                (effect_id, opened_by),
            ).fetchone()
            assert row is not None
            return dict(row)

    # ── T-103 operations: probes, replay claims, authority, journals ──────────

    def record_probe(
        self,
        execution_id: int,
        adapter_id: str,
        declaration_digest: str,
        probe_kind: str,
        query_keys: dict[str, Any],
        result: str,
        *,
        n_found: int | None = None,
        destination_refs: tuple[str, ...] = (),
        response_digest: str | None = None,
    ) -> int:
        with self._conn.transaction(), translated_errors():
            row = self._conn.execute(
                """
                INSERT INTO status_probes (execution_id, adapter_id,
                  declaration_digest, probe_kind, query_keys, result, n_found,
                  destination_refs, response_digest, queried_at)
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, now())
                RETURNING probe_id
                """,
                (
                    execution_id,
                    adapter_id,
                    declaration_digest,
                    probe_kind,
                    Jsonb(query_keys),
                    result,
                    n_found,
                    Jsonb(list(destination_refs)),
                    response_digest,
                ),
            ).fetchone()
            assert row is not None
            return int(row["probe_id"])

    def claim_replay_probe(self, execution_id: int) -> ClaimOutcome:
        """§5.3 item 2: claim a c1_replay_probe attempt on an AMBIGUOUS
        execution, reusing the SAME operation_id/key by design. Same
        slot/open-attempt discipline; no gate decision (C1 M16)."""
        with self._conn.transaction(), translated_errors():
            row = self._conn.execute(
                """
                SELECT e.effect_id, e.operation_id, r.scope, r.effect_type,
                       r.adapter_id, r.declaration_digest
                FROM effect_executions e JOIN effect_records r USING (effect_id)
                WHERE e.execution_id = %s
                """,
                (execution_id,),
            ).fetchone()
            if row is None:
                raise NotFound(f"no execution {execution_id}")
            self._conn.execute(
                "INSERT INTO scope_slots (scope, effect_type) VALUES (%s, %s) "
                "ON CONFLICT DO NOTHING",
                (row["scope"], row["effect_type"]),
            )
            self._conn.execute(
                "SELECT 1 FROM scope_slots WHERE scope = %s AND effect_type = %s "
                "FOR UPDATE",
                (row["scope"], row["effect_type"]),
            )
            self._conn.execute(
                "SELECT 1 FROM effect_records WHERE effect_id = %s FOR UPDATE",
                (row["effect_id"],),
            )
            frontier = self._conn.execute(
                "SELECT frontier FROM execution_frontiers WHERE execution_id = %s",
                (execution_id,),
            ).fetchone()
            if frontier is None or frontier["frontier"] != "AMBIGUOUS":
                raise IllegalState(
                    "c1 replay probe is legal only on an AMBIGUOUS frontier (§5.3)"
                )
            busy = self._conn.execute(
                "SELECT attempt_id FROM open_attempts WHERE scope = %s AND "
                "effect_type = %s LIMIT 1",
                (row["scope"], row["effect_type"]),
            ).fetchone()
            if busy is not None:
                raise ScopeBusy(
                    "an open attempt exists in this slot",
                    details={"attempt_id": busy["attempt_id"]},
                )
            key = derive_idempotency_key(row["operation_id"])
            attempt = self._conn.execute(
                """
                INSERT INTO dispatch_attempts (execution_id, attempt_no, kind,
                  adapter_id, declaration_digest, idempotency_key, request_digest,
                  gate_decision_id)
                VALUES (%s,
                        (SELECT COALESCE(MAX(attempt_no), 0) + 1
                         FROM dispatch_attempts WHERE execution_id = %s),
                        'c1_replay_probe', %s, %s, %s, %s, NULL)
                RETURNING attempt_id, attempt_no
                """,
                (
                    execution_id,
                    execution_id,
                    row["adapter_id"],
                    row["declaration_digest"],
                    key,
                    canonical_digest({"replay_probe": row["operation_id"]}),
                ),
            ).fetchone()
            assert attempt is not None
            return ClaimOutcome(
                outcome="claimed",
                effect_id=row["effect_id"],
                lifecycle="AMBIGUOUS",
                execution_id=execution_id,
                attempt_id=attempt["attempt_id"],
                attempt_no=attempt["attempt_no"],
                operation_id=row["operation_id"],
                idempotency_key=key,
                adapter_id=row["adapter_id"],
            )

    def record_replay_outcome(
        self,
        attempt_id: int,
        transport_outcome: str,
        *,
        actor: str = "reconciler",
        destination_ref: str | None = None,
        response_digest: str | None = None,
        evidence: dict[str, Any] | None = None,
    ) -> OutcomeRecord:
        """Receipt + AMBIGUOUS→settle via replay_ok/replay_failed (§3.1). An
        inconclusive probe (TIMEOUT/LOST) records the receipt and leaves the
        frontier AMBIGUOUS."""
        evidence = evidence or {}
        with self._conn.transaction(), translated_errors():
            attempt = self._conn.execute(
                "SELECT execution_id FROM dispatch_attempts WHERE attempt_id = %s",
                (attempt_id,),
            ).fetchone()
            if attempt is None:
                raise NotFound(f"no attempt {attempt_id}")
            receipt = self._conn.execute(
                """
                INSERT INTO dispatch_receipts (attempt_id, transport_outcome,
                  failure_kind, destination_ref, response_digest, evidence,
                  recorded_by)
                VALUES (%s, %s, %s, %s, %s, %s, %s)
                RETURNING receipt_id
                """,
                (
                    attempt_id,
                    transport_outcome,
                    "TERMINAL" if transport_outcome == "FAILED" else None,
                    destination_ref,
                    response_digest,
                    Jsonb(evidence),
                    "recovery" if actor == "recovery" else "reconciler",
                ),
            ).fetchone()
            assert receipt is not None
            lifecycle = "AMBIGUOUS"
            if transport_outcome in ("OK", "FAILED"):
                to_state = (
                    "SETTLED_COMMITTED" if transport_outcome == "OK" else "SETTLED_FAILED"
                )
                cause = "replay_ok" if transport_outcome == "OK" else "replay_failed"
                self._conn.execute(
                    "SELECT ledger_transition(%s, 'AMBIGUOUS', %s, %s, %s, %s)",
                    (
                        attempt["execution_id"],
                        to_state,
                        cause,
                        actor,
                        Jsonb({"receipt_id": receipt["receipt_id"], **evidence}),
                    ),
                )
                lifecycle = to_state
            return OutcomeRecord(
                settled=lifecycle != "AMBIGUOUS",
                lifecycle=lifecycle,
                receipt_id=receipt["receipt_id"],
            )

    def append_authority(
        self, effect_id: str, authority_ref: str, stamped_at: str
    ) -> None:
        """The sanctioned authority-refresh append (RFC-002 §1) for retry and
        resolve-redispatch paths."""
        with self._conn.transaction(), translated_errors():
            record = self._conn.execute(
                "SELECT scope FROM effect_records WHERE effect_id = %s", (effect_id,)
            ).fetchone()
            if record is None:
                raise NotFound(f"no effect record {effect_id}")
            row = self._conn.execute(
                "INSERT INTO authorities (authority_ref, scope, stamped_at) "
                "VALUES (%s, %s, %s) RETURNING authority_id",
                (authority_ref, record["scope"], stamped_at),
            ).fetchone()
            assert row is not None
            self._conn.execute(
                "INSERT INTO effect_authorities (effect_id, authority_id) "
                "VALUES (%s, %s)",
                (effect_id, row["authority_id"]),
            )

    def resolve_chain(
        self,
        finding_id: int,
        steps: list[tuple[str, str]],
        actor: str,
        evidence: dict[str, Any],
    ) -> None:
        """Multiple resolution edges in ONE transaction (e.g. ACCEPTED_AS_IS
        then CLOSED — §3.3 same-transaction close)."""
        with self._conn.transaction(), translated_errors():
            for from_status, to_status in steps:
                self._conn.execute(
                    "SELECT ledger_resolve(%s, %s, %s, %s, %s)",
                    (finding_id, from_status, to_status, actor, Jsonb(evidence)),
                )

    def open_executions(self) -> list[dict[str, Any]]:
        """Recovery scan: frontier ∈ {DISPATCHED, AMBIGUOUS} in deterministic
        order (§7.1)."""
        with self._conn.transaction():
            return [
                dict(r)
                for r in self._conn.execute(
                    """
                    SELECT f.execution_id, f.effect_id, f.step, f.operation_id,
                           f.frontier
                    FROM execution_frontiers f
                    WHERE f.frontier IN ('DISPATCHED', 'AMBIGUOUS')
                    ORDER BY f.execution_id
                    """
                ).fetchall()
            ]

    def record_sweep_run(
        self,
        adapter_id: str,
        window_from: str,
        window_to: str,
        listed: int,
        matched: int,
        sightings: list[dict[str, Any]],
    ) -> int:
        with self._conn.transaction(), translated_errors():
            run = self._conn.execute(
                """
                INSERT INTO sweep_runs (adapter_id, window_from, window_to, listed,
                  matched)
                VALUES (%s, %s, %s, %s, %s) RETURNING run_id
                """,
                (adapter_id, window_from, window_to, listed, matched),
            ).fetchone()
            assert run is not None
            for s in sightings:
                self._conn.execute(
                    """
                    INSERT INTO sweep_sightings (run_id, adapter_id, destination_ref,
                      payload_digest, matched_effect, match_path)
                    VALUES (%s, %s, %s, %s, %s, %s)
                    ON CONFLICT (run_id, adapter_id, destination_ref) DO NOTHING
                    """,
                    (
                        run["run_id"],
                        adapter_id,
                        s["destination_ref"],
                        s["payload_digest"],
                        s.get("matched_effect"),
                        s.get("match_path"),
                    ),
                )
            return int(run["run_id"])

    def record_recovery_run(
        self, scanned: int, adjudicated: int, parked: int, queued: int
    ) -> None:
        with self._conn.transaction(), translated_errors():
            self._conn.execute(
                """
                INSERT INTO recovery_runs (scanned, adjudicated, parked,
                  queued_redispatches)
                VALUES (%s, %s, %s, %s)
                """,
                (scanned, adjudicated, parked, queued),
            )

    def acquire_writer_lock(self) -> bool:
        """Session-scoped single-writer advisory lock (§7.1). Held by THIS
        connection until close; a second engine process must refuse to start."""
        row = self._conn.execute(
            "SELECT pg_try_advisory_lock(hashtext('irrevon_single_writer')) AS ok"
        ).fetchone()
        self._conn.commit()
        assert row is not None
        return bool(row["ok"])

    # ── Read surface (used by tests, reconcile, recovery, inspect) ────────────

    def _latest_frontier(self, effect_id: str) -> dict[str, Any] | None:
        return self._conn.execute(
            """
            SELECT execution_id, step, operation_id, frontier
            FROM execution_frontiers WHERE effect_id = %s
            ORDER BY step DESC LIMIT 1
            """,
            (effect_id,),
        ).fetchone()

    def _last_receipt(self, execution_id: int) -> dict[str, Any] | None:
        row = self._conn.execute(
            """
            SELECT r.receipt_id, r.transport_outcome, r.failure_kind,
                   r.destination_ref, r.recorded_by, a.attempt_no
            FROM dispatch_receipts r JOIN dispatch_attempts a USING (attempt_id)
            WHERE a.execution_id = %s ORDER BY r.receipt_id DESC LIMIT 1
            """,
            (execution_id,),
        ).fetchone()
        return dict(row) if row else None

    def effect_frontier(self, effect_id: str) -> dict[str, Any]:
        with self._conn.transaction():
            row = self._latest_frontier(effect_id)
        if row is None:
            raise NotFound(f"no effect record {effect_id}")
        return dict(row)

    def effect_record(self, effect_id: str) -> dict[str, Any]:
        with self._conn.transaction():
            row = self._conn.execute(
                "SELECT * FROM effect_records WHERE effect_id = %s", (effect_id,)
            ).fetchone()
        if row is None:
            raise NotFound(f"no effect record {effect_id}")
        return dict(row)

    def execution(self, execution_id: int) -> dict[str, Any]:
        with self._conn.transaction():
            row = self._conn.execute(
                """
                SELECT f.*, r.adapter_id, r.declaration_digest, r.scope,
                       r.effect_type, r.stable_ids
                FROM execution_frontiers f JOIN effect_records r USING (effect_id)
                WHERE f.execution_id = %s
                """,
                (execution_id,),
            ).fetchone()
        if row is None:
            raise NotFound(f"no execution {execution_id}")
        return dict(row)

    def latest_receipt(self, execution_id: int) -> dict[str, Any] | None:
        with self._conn.transaction():
            return self._last_receipt(execution_id)

    def open_attempt(self, execution_id: int) -> dict[str, Any] | None:
        with self._conn.transaction():
            row = self._conn.execute(
                "SELECT * FROM open_attempts WHERE execution_id = %s "
                "ORDER BY attempt_id DESC LIMIT 1",
                (execution_id,),
            ).fetchone()
        return dict(row) if row else None

    def findings_for(self, effect_id: str) -> list[dict[str, Any]]:
        with self._conn.transaction():
            return [
                dict(r)
                for r in self._conn.execute(
                    "SELECT * FROM findings WHERE effect_id = %s ORDER BY finding_id",
                    (effect_id,),
                ).fetchall()
            ]

    def query(self, sql: str, params: tuple[Any, ...] = ()) -> list[dict[str, Any]]:
        """Read-only helper for tests and the inspection surface."""
        with self._conn.transaction():
            return [dict(r) for r in self._conn.execute(sql, params).fetchall()]
