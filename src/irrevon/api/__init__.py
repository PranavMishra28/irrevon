"""Engine composition root (RFC-002 §14 ``api``).

Boot order (§7.1): acquire the single-writer advisory lock (refuse to start on
failure) → crash-recovery replay → accept work. The Engine wires ledger, gate,
dispatcher, reconciler, recovery, resolution, and sweep behind the SDK-shaped
operations (dx-api §2); it never imports ``irrevon.advisory`` (import-linter
enforced).
"""

from __future__ import annotations

from typing import Any

from irrevon.adapters.base import Adapter
from irrevon.dispatcher import DispatchReport, dispatch, open_retry_execution
from irrevon.errors import CapabilityUnsupported, StorageUnavailable
from irrevon.ledger import Ledger, Registration
from irrevon.logging import emit
from irrevon.reconciler import (
    ReconcileConfig,
    ReconcileReport,
    audit_effect,
    reconcile_effect,
)
from irrevon.recovery import RecoveryResult, run_recovery
from irrevon.resolution import ResolutionConfig, resolve
from irrevon.sweep import SweepReport, sweep

__all__ = ["Engine"]


class Engine:
    def __init__(
        self,
        dsn: str,
        adapters: dict[str, Adapter],
        *,
        reconcile_config: ReconcileConfig | None = None,
        resolution_config: ResolutionConfig | None = None,
    ) -> None:
        self.ledger = Ledger(dsn)
        self.adapters = adapters
        self.reconcile_config = reconcile_config or ReconcileConfig()
        self.resolution_config = resolution_config or ResolutionConfig(
            reconcile=self.reconcile_config
        )

    def boot(self) -> RecoveryResult:
        """Writer lock + recovery replay BEFORE any work is accepted (§7.1)."""
        if not self.ledger.acquire_writer_lock():
            emit("engine_refused", severity="ERROR", reason="writer_lock_held")
            raise StorageUnavailable(
                "another engine process holds the single-writer lock (§7.1)"
            )
        result = run_recovery(
            self.ledger,
            self.adapters,
            config=self.reconcile_config,
            resolution_config=self.resolution_config,
        )
        emit(
            "recovery_completed",
            scanned=result.scanned,
            adjudicated=result.adjudicated,
            parked=result.parked,
            drained=len(result.drained),
        )
        return result

    def close(self) -> None:
        self.ledger.close()

    def __enter__(self) -> Engine:
        return self

    def __exit__(self, *exc: object) -> None:
        self.close()

    # ── SDK-shaped operations (dx-api §2) ─────────────────────────────────────

    def _adapter_for(self, adapter_id: str) -> Adapter:
        adapter = self.adapters.get(adapter_id)
        if adapter is None:
            raise CapabilityUnsupported(f"no configured adapter {adapter_id!r}")
        return adapter

    def register_intent(self, raw: object) -> Registration:
        adapter_id = raw.get("adapter_id", "") if isinstance(raw, dict) else ""
        adapter = self._adapter_for(str(adapter_id))
        registration = self.ledger.register_intent(raw, adapter.declaration_digest())
        emit(
            "intent_registered",
            effect_id=registration.effect_id,
            operation_id=registration.operation_id,
            lifecycle=registration.lifecycle,
            replayed=registration.replayed,
        )
        return registration

    def dispatch(self, effect_id: str) -> DispatchReport:
        record = self.ledger.effect_record(effect_id)
        adapter = self._adapter_for(record["adapter_id"])
        report = dispatch(self.ledger, adapter, effect_id)
        if report.outcome == "denied":
            emit(
                "gate_decision",
                severity="WARN",
                effect_id=effect_id,
                outcome="DENY",
                deny_check=report.claim.deny_check,
            )
        else:
            emit(
                "dispatched",
                effect_id=effect_id,
                lifecycle=report.lifecycle,
                transport_outcome=report.transport_outcome,
            )
            if report.lifecycle == "AMBIGUOUS":
                emit("ambiguous_parked", severity="WARN", effect_id=effect_id)
        return report

    def reconcile(self, effect_id: str, *, mode: str = "online") -> ReconcileReport:
        record = self.ledger.effect_record(effect_id)
        adapter = self._adapter_for(record["adapter_id"])
        report = reconcile_effect(
            self.ledger, adapter, effect_id, mode=mode, config=self.reconcile_config
        )
        for settled in report.settled:
            emit("settled", severity="WARN", **settled)
        for finding_id in report.findings:
            emit("finding_created", severity="WARN", finding_id=finding_id)
        return report

    def audit(self, effect_id: str) -> ReconcileReport:
        record = self.ledger.effect_record(effect_id)
        adapter = self._adapter_for(record["adapter_id"])
        return audit_effect(self.ledger, adapter, effect_id)

    def sweep(self, adapter_id: str, window_from: str, window_to: str) -> SweepReport:
        adapter = self._adapter_for(adapter_id)
        report = sweep(self.ledger, adapter, window_from, window_to)
        emit(
            "sweep_completed",
            adapter_id=adapter_id,
            listed=report.listed,
            matched=report.matched,
            new_findings=len(report.new_findings),
        )
        return report

    def resolve(
        self,
        finding_id: int,
        action: str,
        evidence: dict[str, Any],
        *,
        actor: str = "human",
    ) -> dict[str, Any]:
        result = resolve(
            self.ledger,
            self.adapters,
            finding_id,
            action,
            evidence,
            actor=actor,
            config=self.resolution_config,
        )
        emit("finding_resolved", finding_id=finding_id, status=result["status"])
        return result

    def open_retry(self, effect_id: str, authority_evidence: dict[str, Any]) -> dict[str, Any]:
        return open_retry_execution(self.ledger, effect_id, authority_evidence)

    def status(self, effect_id: str) -> dict[str, Any]:
        """Read-only composed view (dx-api §2.6): record + receipts + findings
        + current classification. No destination call."""
        record = self.ledger.effect_record(effect_id)
        frontier = self.ledger.effect_frontier(effect_id)
        receipts = self.ledger.query(
            """
            SELECT r.*, a.attempt_no, a.kind, a.idempotency_key, a.execution_id,
                   e.operation_id
            FROM dispatch_receipts r
            JOIN dispatch_attempts a USING (attempt_id)
            JOIN effect_executions e USING (execution_id)
            WHERE e.effect_id = %s ORDER BY r.receipt_id
            """,
            (effect_id,),
        )
        findings = self.ledger.findings_for(effect_id)
        classification = "UNRECONCILED"
        if findings:
            classification = findings[-1]["classification"]
        return {
            "schema_version": "1",
            "record": {
                "effect_id": record["effect_id"],
                "operation_id": frontier["operation_id"],
                "step": frontier["step"],
                "effect_type": record["effect_type"],
                "effect_class": record["effect_class"],
                "scope": record["scope"],
                "stable_ids": dict(record["stable_ids"]),
                "adapter_id": record["adapter_id"],
                "lifecycle": frontier["frontier"],
            },
            "receipts": receipts,
            "findings": findings,
            "classification": classification,
        }
