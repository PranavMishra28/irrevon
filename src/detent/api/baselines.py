"""B5 baseline operationalization — the honest contrast leg.

B5 models the STRONGEST conventional stack (master doc §8; RFC-001 §9.5):
a durable-execution-style runtime with stable workflow op-IDs, a durable
journal, and native idempotency keys sent on every attempt. Its recovery
semantics are the industry's: an activity with an unknown outcome is retried
with the SAME op-ID and idempotency key (at-least-once delivery + key-based
dedup). On C1 destinations that is exactly right. On C2 — where the key is
accepted but not honored — the retry creates a second effect. That residue is
the project's wedge.

One operationalization serves both the demo/E2E contrast leg and (at M5) the
benchmark harness — sharing prevents a "demo B5" weaker than the "benchmark
B5" (testing.md §8, baseline-weakening by the back door).

This module deliberately does NOT import the ledger/gate/reconciler: B5 is a
baseline, not Detent.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from detent.adapters.base import Adapter, DispatchOrder

__all__ = ["B5DurableRuntime"]


class B5DurableRuntime:
    """Durable journal + stable op-IDs + native idempotency keys.

    The journal survives "process death" (file-backed); ``recover()`` re-runs
    every op without a recorded outcome using the same op-ID/key — faithful
    durable-execution retry semantics, NOT a strawman: the key IS sent; a C1
    destination would dedup it (verified by the test-of-the-test with keys
    honored).
    """

    def __init__(self, journal_path: Path, adapter: Adapter) -> None:
        self._journal_path = journal_path
        self._adapter = adapter

    def _read_journal(self) -> dict[str, dict[str, Any]]:
        if self._journal_path.exists():
            loaded = json.loads(self._journal_path.read_text(encoding="utf-8"))
            return dict(loaded)
        return {}

    def _write_journal(self, journal: dict[str, dict[str, Any]]) -> None:
        self._journal_path.write_text(json.dumps(journal, indent=1), encoding="utf-8")

    def execute(
        self, op_id: str, effect_type: str, payload: dict[str, Any]
    ) -> dict[str, Any]:
        """One workflow activity: journal the op durably BEFORE the wire call
        (durable execution), send with the stable op-ID as idempotency key,
        journal the outcome if a response arrives."""
        journal = self._read_journal()
        journal.setdefault(
            op_id,
            {"effect_type": effect_type, "payload": payload, "outcome": None,
             "attempts": 0},
        )
        self._write_journal(journal)
        return self._attempt(op_id)

    def _attempt(self, op_id: str) -> dict[str, Any]:
        journal = self._read_journal()
        op = journal[op_id]
        op["attempts"] += 1
        self._write_journal(journal)
        result = self._adapter.dispatch(
            DispatchOrder(
                operation_id=op_id,
                effect_type=op["effect_type"],
                payload=dict(op["payload"]),
                client_ref=op_id,  # stable op-ID stamped + sent as the key
            ),
            deadline_s=10.0,
        )
        if result.transport_outcome in ("OK", "FAILED"):
            journal = self._read_journal()
            journal[op_id]["outcome"] = {
                "transport_outcome": result.transport_outcome,
                "destination_ref": result.destination_ref,
            }
            self._write_journal(journal)
        # TIMEOUT/LOST: no outcome recorded — recovery will retry (that is the
        # durable-execution model under test; do not "fix" it here).
        return {
            "op_id": op_id,
            "transport_outcome": result.transport_outcome,
            "destination_ref": result.destination_ref,
        }

    def recover(self) -> list[dict[str, Any]]:
        """Restart semantics: retry every op without a recorded outcome, same
        op-ID, same key. On C2 this is where the duplicate happens."""
        journal = self._read_journal()
        retried = []
        for op_id, op in sorted(journal.items()):
            if op["outcome"] is None:
                retried.append(self._attempt(op_id))
        return retried
