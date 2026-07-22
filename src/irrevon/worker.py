"""``irrevon worker`` — the continuous reconciliation service (ADR-0034, proposed).

Moves the engine from manually invoked commands to a long-running,
operator-grade service loop, WITHOUT changing the ratified single-writer
invariant (ADR-002): the worker IS the single writer, guarded by the same
session advisory lock the Engine boot acquires — a second worker refuses to
start. The multi-worker graduation (scope leases claimed with
``FOR UPDATE SKIP LOCKED``, heartbeats, and epoch-fenced ledger transitions)
is DESIGNED in ADR-0034 and deliberately not implemented until the human
reopens ADR-002 for a multi-writer deployment.

Each cycle, in order:

1. **Reconcile scheduling** — every open execution (frontier DISPATCHED /
   AMBIGUOUS) is adjudicated through the normal online reconcile path (which
   itself enforces the stuck threshold, confirmed-absence protocol, and
   re-read gaps; delayed rereads are exactly re-visits on later cycles).
2. **Orphan sweeps** — per adapter with ``list_queryable``, on the sweep
   interval, with overlap-windowed ranges (RFC-002 §7.2).
3. **Operational gauges** — queue depth, oldest-open-work age, oldest
   unresolved-ambiguous age, and OPEN finding counts are emitted as
   structured events every cycle (the observability catalog, ADR-0034), and
   the health file is refreshed (freshness-file liveness pattern for
   non-HTTP workers; Kubernetes exec/liveness probes stat it).

Shutdown: SIGTERM/SIGINT set a stop flag; the current cycle finishes (wire
calls are short and never hold transactions, RFC-002 §5.1); the engine
closes; exit 0. No new work is claimed after the signal.
"""

from __future__ import annotations

import json
import signal
import time
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from pathlib import Path
from types import FrameType
from typing import Any

from irrevon.adapters.base import Adapter
from irrevon.api import Engine
from irrevon.errors import IrrevonError
from irrevon.logging import emit

__all__ = ["WorkerConfig", "run_worker"]


@dataclass(frozen=True)
class WorkerConfig:
    """Tunables are operational, not architectural (RFC-002 §13 discipline)."""

    reconcile_interval_s: float = 30.0
    sweep_interval_s: float = 300.0
    sweep_overlap_s: float = 600.0
    health_file: Path | None = None
    # None = run until signalled; tests and one-shot operations set a bound.
    max_cycles: int | None = None


def _now_iso() -> str:
    return datetime.now(UTC).isoformat().replace("+00:00", "Z")


def _gauges(engine: Engine) -> dict[str, Any]:
    """Operational gauges over the ledger (read-only; low-cardinality names)."""
    rows = engine.ledger.query(
        """
        SELECT
          count(*) FILTER (WHERE frontier IN ('DISPATCHED','AMBIGUOUS'))
            AS open_executions,
          count(*) FILTER (WHERE frontier = 'AMBIGUOUS') AS ambiguous_executions
        FROM execution_frontiers
        """
    )
    age_rows = engine.ledger.query(
        """
        SELECT EXTRACT(EPOCH FROM (now() - min(e.created_at))) AS oldest_open_age_s
        FROM execution_frontiers f
        JOIN effect_executions e USING (execution_id)
        WHERE f.frontier IN ('DISPATCHED','AMBIGUOUS')
        """
    )
    finding_rows = engine.ledger.query(
        """
        SELECT count(*) AS open_findings FROM findings f
        WHERE NOT EXISTS (
          SELECT 1 FROM finding_resolutions r
          WHERE r.finding_id = f.finding_id AND r.to_status = 'CLOSED'
        )
        """
    )
    oldest = age_rows[0]["oldest_open_age_s"]
    return {
        "open_executions": int(rows[0]["open_executions"]),
        "ambiguous_executions": int(rows[0]["ambiguous_executions"]),
        "oldest_open_age_s": float(oldest) if oldest is not None else None,
        "open_findings": int(finding_rows[0]["open_findings"]),
    }


def _touch_health(path: Path | None, cycle: int, gauges: dict[str, Any]) -> None:
    if path is None:
        return
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps(
            {"schema_version": "1", "at": _now_iso(), "cycle": cycle, **gauges}
        )
        + "\n",
        encoding="utf-8",
    )


def run_worker(
    dsn: str,
    adapters: dict[str, Adapter],
    config: WorkerConfig | None = None,
) -> int:
    """Run the continuous service loop; returns a process exit code."""
    import threading

    config = config or WorkerConfig()
    stop_event = threading.Event()
    stop_signal: list[str] = []

    def _handle(signum: int, _frame: FrameType | None) -> None:
        stop_signal.append(signal.Signals(signum).name)
        stop_event.set()
        emit("worker.stop_requested", severity="WARN", signal=stop_signal[-1])

    previous = {
        signal.SIGTERM: signal.signal(signal.SIGTERM, _handle),
        signal.SIGINT: signal.signal(signal.SIGINT, _handle),
    }
    try:
        with Engine(dsn, adapters) as engine:
            recovery = engine.boot()  # writer lock + recovery replay (§7.1)
            emit(
                "worker.started",
                recovery_scanned=recovery.scanned,
                reconcile_interval_s=config.reconcile_interval_s,
                sweep_interval_s=config.sweep_interval_s,
            )
            cycle = 0
            last_sweep = 0.0
            while not stop_event.is_set():
                cycle += 1
                cycle_started = time.monotonic()

                # 1. Reconcile every open execution through the normal online
                #    path (it enforces stuck thresholds and re-read gaps; a
                #    still-young or still-parked record simply comes back next
                #    cycle — the delayed-reread schedule).
                adjudicated = 0
                escalated = 0
                for row in engine.ledger.open_executions():
                    if stop_event.is_set():
                        break
                    try:
                        report = engine.reconcile(row["effect_id"])
                    except IrrevonError as err:
                        emit(
                            "worker.reconcile_error",
                            severity="ERROR",
                            effect_id=row["effect_id"],
                            error=type(err).__name__,
                        )
                        continue
                    adjudicated += len(report.settled)
                    escalated += len(report.escalated)

                # 2. Orphan sweeps on their own interval.
                if (
                    not stop_event.is_set()
                    and time.monotonic() - last_sweep >= config.sweep_interval_s
                ):
                    last_sweep = time.monotonic()
                    window_to = datetime.now(UTC)
                    window_from = window_to - timedelta(
                        seconds=config.sweep_interval_s + config.sweep_overlap_s
                    )
                    for adapter_id, adapter in sorted(adapters.items()):
                        if not adapter.declare().get("list_queryable"):
                            continue
                        try:
                            engine.sweep(
                                adapter_id,
                                window_from.isoformat().replace("+00:00", "Z"),
                                window_to.isoformat().replace("+00:00", "Z"),
                            )
                        except IrrevonError as err:
                            emit(
                                "worker.sweep_error",
                                severity="ERROR",
                                adapter_id=adapter_id,
                                error=type(err).__name__,
                            )

                # 3. Gauges + health freshness.
                gauges = _gauges(engine)
                emit(
                    "worker.cycle",
                    cycle=cycle,
                    duration_ms=round((time.monotonic() - cycle_started) * 1000, 1),
                    adjudicated=adjudicated,
                    escalated=escalated,
                    **gauges,
                )
                _touch_health(config.health_file, cycle, gauges)

                if config.max_cycles is not None and cycle >= config.max_cycles:
                    emit("worker.completed", cycles=cycle)
                    return 0
                deadline = time.monotonic() + config.reconcile_interval_s
                while not stop_event.is_set() and time.monotonic() < deadline:
                    time.sleep(min(0.2, config.reconcile_interval_s))
            emit("worker.stopped", severity="WARN",
                 signal=stop_signal[-1] if stop_signal else None, cycles=cycle)
            return 0
    finally:
        for signum, handler in previous.items():
            signal.signal(signum, handler)
