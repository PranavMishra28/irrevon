"""JSONL structured logging (RFC-002 §11) — the v0.1 observability surface.

One JSON object per line, stderr by default (optional file sink via
``IRREVON_LOG_FILE``). Stable ``event_name`` catalog; identifier privacy rule:
Irrevon-minted identifiers raw, upstream values digested or absent, payload
bodies never. Severity discipline: ERROR = Irrevon malfunctioning; WARN = the
system working and finding something (AMBIGUOUS, denies, findings).

Logs are diagnostics: NO decision path reads them; the ledger is the sole
source of truth; crash recovery is ledger replay, never log replay.
"""

from __future__ import annotations

import json
import os
import sys
from datetime import UTC, datetime
from typing import Any, TextIO

__all__ = ["EVENT_NAMES", "emit"]

EVENT_NAMES = frozenset(
    {
        "intent_registered",
        "gate_decision",
        "dispatched",
        "settled",
        "ambiguous_parked",
        "finding_created",
        "finding_resolved",
        "escalated",
        "recovery_completed",
        "sweep_completed",
        "engine_refused",
    }
)


def _sink() -> TextIO:
    path = os.environ.get("IRREVON_LOG_FILE")
    if path:
        return open(path, "a", encoding="utf-8")
    return sys.stderr


def emit(event_name: str, severity: str = "INFO", **fields: Any) -> None:
    if event_name not in EVENT_NAMES:
        raise ValueError(f"unknown event_name {event_name!r} (stable catalog)")
    record = {
        "ts": datetime.now(UTC).isoformat().replace("+00:00", "Z"),
        "event_name": event_name,
        "severity": severity,
        **fields,
    }
    sink = _sink()
    print(json.dumps(record, default=str), file=sink, flush=True)
    if sink is not sys.stderr:
        sink.close()
