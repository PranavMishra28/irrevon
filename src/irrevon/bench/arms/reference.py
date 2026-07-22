"""Arm R — the Irrevon reference engine as a benchmark subject.

The driver exercises the engine through its PUBLIC composition root
(``irrevon.api.Engine``) exactly as an integrator would: register → dispatch →
reconcile, with recovery-on-boot for crash episodes. It receives no oracle
data and no fixture labels (import-linter enforced).

Known deviations (recorded in the spec, surfaced in every run manifest):

- Process death is simulated in-process: the engine's connection is closed
  mid-flight (open attempt left durable, no receipt) and a fresh Engine boots
  through the real recovery replay. The kernel-SIGKILL coverage of the same
  seams lives in tests/process/ and tests/e2e/ and in ``irrevon demo``.
- stale-authorization is enacted by backdating the authority stamp beyond the
  default 24h freshness policy (migrations 0002) — the gate's real freshness
  check does the denying; no driver-level shortcut.
"""

from __future__ import annotations

from datetime import UTC, datetime, timedelta
from typing import Any

import psycopg
from psycopg import sql

from irrevon.adapters.base import Adapter, DispatchOrder, DispatchResult
from irrevon.api import Engine
from irrevon.bench.arms import ArmDriver, ArmSpec, Episode, TrialReport
from irrevon.ledger.db import apply_migrations
from irrevon.reconciler import ReconcileConfig

__all__ = ["REFERENCE_SPEC", "ReferenceArm", "SimulatedProcessDeath"]

REFERENCE_SPEC = ArmSpec(
    arm_id="R",
    description=(
        "Irrevon reference engine: stable-id identity, persist-before-dispatch "
        "ledger, deterministic commit gate, reconcile-by-query, recovery replay."
    ),
    version="0.1.0",
    retry_behavior=(
        "never re-dispatch on belief: in-flight retries return "
        "pending_reconciliation; settled retries are evidenced dedup denies; "
        "redispatch only after confirmed absence + fresh authority"
    ),
    operationalized=True,
    requires_postgres=True,
    ambiguity_concept=True,
    classifies=True,
    known_deviations=(
        "bench crash episodes simulate process death in-process (connection "
        "closed mid-flight; recovery replay on a fresh Engine); kernel-SIGKILL "
        "coverage of the same seams lives in tests/process/ and tests/e2e/",
        "stale-authorization enacted via a backdated authority stamp against "
        "the default 24h freshness policy",
    ),
    config={"reconcile": {"absence_reread_gap_s": 0.0, "stuck_threshold_s": 0.0}},
)


class SimulatedProcessDeath(RuntimeError):
    """Raised by the crash wrapper AFTER destination commit, BEFORE the receipt
    write — leaving the durable open attempt exactly as a real mid-flight
    process death would."""


class _CrashOnceAdapter(Adapter):
    """Delegating wrapper that dies (once, when armed) between the wire call
    and the receipt — the crash-after-effect-before-response seam."""

    def __init__(self, inner: Adapter) -> None:
        self._inner = inner
        self.adapter_id = inner.adapter_id
        self._armed = False

    def arm(self) -> None:
        self._armed = True

    def declare(self) -> dict[str, Any]:
        return self._inner.declare()

    def declaration_digest(self) -> str:
        return self._inner.declaration_digest()

    def dispatch(self, order: DispatchOrder, deadline_s: float) -> DispatchResult:
        result = self._inner.dispatch(order, deadline_s)
        if self._armed:
            self._armed = False
            raise SimulatedProcessDeath(
                "process death after destination effect, before response record"
            )
        return result

    def status_query(self, **kwargs: Any) -> Any:
        return self._inner.status_query(**kwargs)

    def list_effects(self, *args: Any, **kwargs: Any) -> list[dict[str, Any]]:
        return self._inner.list_effects(*args, **kwargs)


class ReferenceArm(ArmDriver):
    spec = REFERENCE_SPEC

    def __init__(self, adapter: Adapter, admin_dsn: str) -> None:
        self._crash_adapter = _CrashOnceAdapter(adapter)
        self._admin_dsn = admin_dsn
        self._engine: Engine | None = None
        self._dsn = ""
        self._db_name = ""

    # ── unit lifecycle: fresh ledger database per unit ─────────────────────────

    def begin_unit(self, unit_seed: int) -> None:
        self._db_name = f"irrevon_bench_{unit_seed % 10**12}"
        with psycopg.connect(self._admin_dsn, autocommit=True) as admin:
            admin.execute(
                sql.SQL("DROP DATABASE IF EXISTS {}").format(sql.Identifier(self._db_name))
            )
            admin.execute(
                sql.SQL("CREATE DATABASE {}").format(sql.Identifier(self._db_name))
            )
        self._dsn = psycopg.conninfo.make_conninfo(self._admin_dsn, dbname=self._db_name)
        apply_migrations(self._dsn)
        self._boot()

    def _boot(self) -> None:
        self._engine = Engine(
            self._dsn,
            {self._crash_adapter.adapter_id: self._crash_adapter},
            reconcile_config=ReconcileConfig(
                stuck_threshold_s=0.0, absence_reread_gap_s=0.0
            ),
        )
        self._engine.boot()

    def end_unit(self) -> None:
        if self._engine is not None:
            self._engine.close()
            self._engine = None
        with psycopg.connect(self._admin_dsn, autocommit=True) as admin:
            admin.execute(
                """
                SELECT pg_terminate_backend(pid) FROM pg_stat_activity
                WHERE datname = %s AND pid <> pg_backend_pid()
                """,
                (self._db_name,),
            )
            admin.execute(
                sql.SQL("DROP DATABASE IF EXISTS {}").format(sql.Identifier(self._db_name))
            )

    # ── contract building (the integrator surface) ─────────────────────────────

    def _contract(
        self, episode: Episode, parameters: dict[str, Any], authority_ref: str, *,
        backdate_authority: bool,
    ) -> dict[str, Any]:
        stamped = datetime.now(UTC) - (timedelta(hours=48) if backdate_authority else timedelta())
        contract: dict[str, Any] = {
            "schema_version": "1",
            "stable_ids": dict(episode.stable_ids),
            "effect_type": episode.effect_type,
            "effect_class": episode.effect_class,
            "scope": episode.scope,
            "adapter_id": self._crash_adapter.adapter_id,
            "parameters": parameters,
            "authority_ref": authority_ref,
            "stamped_at": stamped.isoformat().replace("+00:00", "Z"),
        }
        if episode.branch_ref is not None:
            contract["branch_ref"] = episode.branch_ref
        return contract

    # ── the episode ────────────────────────────────────────────────────────────

    def run_episode(self, episode: Episode) -> TrialReport:
        assert self._engine is not None
        log: list[dict[str, Any]] = []
        report = TrialReport(
            trial_index=episode.trial_index,
            arm_outcome="unresolved-unknown",
            dispatch_attempted=False,
            detail={"log": log, "authority_concept": True, "branch_concept": True},
        )

        registration = self._engine.register_intent(
            self._contract(
                episode,
                dict(episode.parameters),
                episode.authority_ref,
                backdate_authority=episode.authority_expired,
            )
        )
        effect_id = registration.effect_id
        log.append({"action": "register", "effect_id": effect_id})

        if episode.branch_cancelled and episode.branch_ref is not None:
            # The upstream workflow cancels the branch between intent and
            # dispatch (T_DISPATCH anchor); the gate must catch it.
            self._engine.ledger.query(
                "INSERT INTO branch_cancellations (branch_ref, reason) "
                "VALUES (%s, %s) RETURNING branch_ref",
                (episode.branch_ref, "benchmark: branch cancelled pre-dispatch"),
            )
            log.append({"action": "cancel-branch", "branch_ref": episode.branch_ref})

        if episode.fault == "crash-after-effect-before-response":
            self._crash_adapter.arm()
            try:
                self._engine.dispatch(effect_id)
            except SimulatedProcessDeath:
                report.dispatch_attempted = True
                log.append({"action": "crash", "at": "post-effect-pre-receipt"})
                self._engine.close()
                self._boot()  # recovery replay adjudicates BEFORE new work
                log.append({"action": "recovered"})
            return self._agent_retry(episode, effect_id, report, log)

        first = self._engine.dispatch(effect_id)
        report.dispatch_attempted = first.outcome == "dispatched"
        log.append(
            {
                "action": "dispatch",
                "outcome": first.outcome,
                "lifecycle": first.lifecycle,
                "deny_check": first.claim.deny_check,
            }
        )
        if first.outcome == "denied":
            # Authority/branch deny: the correct pre-dispatch abort.
            report.arm_outcome = "suppressed"
            report.detail["deny_check"] = first.claim.deny_check
            return report
        if first.lifecycle == "SETTLED_COMMITTED":
            report.arm_outcome = "committed"
            if episode.fault in ("retry-storm", "semantic-resynthesis"):
                return self._agent_retry(episode, effect_id, report, log)
            return report
        if first.lifecycle == "SETTLED_FAILED":
            report.arm_outcome = "failed"
            return report

        # AMBIGUOUS: storm retries never reach the wire; reconcile adjudicates.
        if episode.fault == "retry-storm":
            for _ in range(max(1, episode.retries)):
                storm = self._engine.dispatch(effect_id)
                log.append({"action": "storm-retry", "outcome": storm.outcome})
        return self._reconcile_then_retry(episode, effect_id, report, log)

    def _reconcile_then_retry(
        self,
        episode: Episode,
        effect_id: str,
        report: TrialReport,
        log: list[dict[str, Any]],
    ) -> TrialReport:
        assert self._engine is not None
        reconcile = self._engine.reconcile(effect_id)
        log.append(
            {
                "action": "reconcile",
                "settled": reconcile.settled,
                "escalated": reconcile.escalated,
                "still_ambiguous": reconcile.still_ambiguous,
            }
        )
        frontier = self._engine.ledger.effect_frontier(effect_id)["frontier"]
        if frontier == "AMBIGUOUS":
            report.arm_outcome = "escalated" if reconcile.escalated else "ambiguous-unresolved"
            return report
        report.arm_outcome = "committed" if frontier == "SETTLED_COMMITTED" else "failed"
        # The oracle-checkable claim the reconcile settle just made (§4
        # false-reconciliation input): committed ⇒ exactly-one, failed ⇒ absent.
        report.detail["oracle_claim"] = (
            "unique" if frontier == "SETTLED_COMMITTED" else "absent"
        )
        return self._agent_retry(episode, effect_id, report, log)

    def _agent_retry(
        self,
        episode: Episode,
        effect_id: str,
        report: TrialReport,
        log: list[dict[str, Any]],
    ) -> TrialReport:
        """The agent-side retry that closes every faulted episode: possibly
        re-synthesized arguments, same stable ids — identity collapses to the
        same effect_id and the gate answers with evidence, never a second
        effect."""
        assert self._engine is not None
        if episode.fault is None:
            return report
        parameters = (
            dict(episode.resynth_parameters)
            if episode.resynth_parameters is not None
            else dict(episode.parameters)
        )
        stable_ids = episode.resynth_stable_ids or episode.stable_ids
        retry_episode_contract = self._contract(
            episode,
            parameters,
            f"{episode.authority_ref}-retry",
            backdate_authority=False,
        )
        retry_episode_contract["stable_ids"] = dict(stable_ids)
        retry = self._engine.register_intent(retry_episode_contract)
        result = self._engine.dispatch(retry.effect_id)
        log.append(
            {
                "action": "agent-retry",
                "same_effect_id": retry.effect_id == effect_id,
                "replayed": retry.replayed,
                "outcome": result.outcome,
                "deny_check": result.claim.deny_check,
                "lifecycle": result.lifecycle,
            }
        )
        if report.arm_outcome == "unresolved-unknown":
            frontier = self._engine.ledger.effect_frontier(effect_id)["frontier"]
            if frontier == "SETTLED_COMMITTED":
                report.arm_outcome = "committed"
                report.detail["oracle_claim"] = "unique"
        return report
