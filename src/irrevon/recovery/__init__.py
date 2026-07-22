"""Crash-recovery replay (RFC-002 §7.1).

At process start, BEFORE the API accepts work: acquire the session-scoped
single-writer advisory lock (refuse to start on failure); scan for executions
with frontier ∈ {DISPATCHED, AMBIGUOUS} in deterministic order; adjudicate each
per §6 (at boot every open attempt is provably abandoned, so recovery may close
it with a LOST receipt); park what cannot be adjudicated; queue — but do not
execute — policy redispatches until the whole scan is adjudicated; then drain
the queue through §5.3. Recovery is re-entrant from any crash point: every
write is guarded by the locked functions and unique arbiters, and the scan
predicate shrinks monotonically.
"""

from __future__ import annotations

from dataclasses import dataclass, field

from irrevon.adapters.base import Adapter
from irrevon.errors import StorageUnavailable
from irrevon.ledger import Ledger
from irrevon.reconciler import ReconcileConfig, reconcile_effect
from irrevon.resolution import ResolutionConfig, resolve
from irrevon.testhooks import crashpoint

__all__ = ["RecoveryResult", "run_recovery"]


@dataclass(slots=True)
class RecoveryResult:
    scanned: int = 0
    adjudicated: int = 0
    parked: int = 0
    queued_redispatches: list[int] = field(default_factory=list)
    drained: list[int] = field(default_factory=list)


def run_recovery(
    ledger: Ledger,
    adapters: dict[str, Adapter],
    *,
    config: ReconcileConfig | None = None,
    resolution_config: ResolutionConfig | None = None,
) -> RecoveryResult:
    """The caller must already hold the writer lock (Ledger.acquire_writer_lock);
    this function refuses to run without it — enforced, not assumed."""
    config = config or ReconcileConfig()
    resolution_config = resolution_config or ResolutionConfig()
    if not _holds_writer_lock(ledger):
        raise StorageUnavailable(
            "recovery requires the single-writer advisory lock (§7.1); another "
            "engine process holds it — refusing to start"
        )

    result = RecoveryResult()
    seen_effects: set[str] = set()
    open_execs = ledger.open_executions()
    result.scanned = len(open_execs)

    for execution in open_execs:
        effect_id = execution["effect_id"]
        if effect_id in seen_effects:
            continue
        seen_effects.add(effect_id)
        record = ledger.effect_record(effect_id)
        adapter = adapters[record["adapter_id"]]
        report = reconcile_effect(
            ledger, adapter, effect_id, mode="recovery", config=config
        )
        if report.settled:
            result.adjudicated += 1
        else:
            result.parked += len(report.still_ambiguous)
        # Queue (never execute mid-scan) automatic redispatches for LOST
        # findings that meet the §5.3-3 policy_auto preconditions.
        for finding_id in report.findings:
            finding = ledger.query(
                "SELECT classification FROM findings WHERE finding_id = %s",
                (finding_id,),
            )
            if (
                finding
                and finding[0]["classification"] == "LOST"
                and _policy_auto_allowed(
                    adapter, record["effect_type"], resolution_config
                )
            ):
                result.queued_redispatches.append(finding_id)
        # Seam: after the nth record is adjudicated during replay (§3.3).
        crashpoint("recovery.after_record")

    # Scan fully adjudicated: drain the redispatch queue through §5.3 item 3.
    for finding_id in result.queued_redispatches:
        outcome = resolve(
            ledger,
            adapters,
            finding_id,
            "REDISPATCHED",
            {
                "note": "policy_auto redispatch after recovery-confirmed absence",
                "fresh_authority_ref": f"auth_recovery_{finding_id}",
                "stamped_at": _db_now(ledger),
            },
            actor="policy_auto",
            config=resolution_config,
        )
        result.drained.append(finding_id)
        _ = outcome

    ledger.record_recovery_run(
        result.scanned,
        result.adjudicated,
        result.parked,
        len(result.queued_redispatches),
    )
    return result


def _holds_writer_lock(ledger: Ledger) -> bool:
    # Advisory locks are reentrant within a session: if this session already
    # holds the writer lock this stacks (harmless); if ANOTHER session holds
    # it, the try fails and recovery refuses to start.
    return ledger.acquire_writer_lock()


def _db_now(ledger: Ledger) -> str:
    rows = ledger.query("SELECT now() AS now")
    stamped: str = rows[0]["now"].isoformat().replace("+00:00", "Z")
    return stamped


def _policy_auto_allowed(
    adapter: Adapter, effect_type: str, config: ResolutionConfig
) -> bool:
    """§5.3-3: automatic redispatch-on-absence requires a FINITE declared
    status_settlement_lag AND per-effect-type opt-in — never default."""
    declaration = adapter.declare()
    if declaration["consistency"]["status_settlement_lag"] is None:
        return False
    return effect_type in config.auto_redispatch_effect_types
