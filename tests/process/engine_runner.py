"""Engine-as-a-real-subprocess for the process-level fault suites
(testing.md §3.2). Boot order per RFC-002 §7.1: writer lock → recovery →
READY. Stdout carries the line-oriented sentinel protocol; commands arrive on
stdin. This is TEST HARNESS wiring — the product composition root is
``detent.api`` (T-104); the engine mechanics under test are the real modules.

Protocol:
  stdout: "RECOVERY DONE <json>", "READY", "RESULT <json>", "HOOK <seam> REACHED"
  stdin:  REGISTER <contract-json> | DISPATCH <effect_id> | RECONCILE <effect_id>
          | SWEEP <from> <to> | EXIT
"""

from __future__ import annotations

import json
import os
import sys
from dataclasses import asdict
from typing import Any

from detent.adapters.base import declarations_dir, load_declaration
from detent.adapters.refdest import RefdestAdapter
from detent.errors import DetentError
from detent.ledger import Ledger
from detent.reconciler import ReconcileConfig, reconcile_effect
from detent.recovery import run_recovery
from detent.resolution import ResolutionConfig
from detent.sweep import sweep as run_sweep
from detent.testhooks import assert_arming_sane


def _config() -> ReconcileConfig:
    return ReconcileConfig(
        stuck_threshold_s=float(os.environ.get("DETENT_STUCK_THRESHOLD_S", "300")),
        absence_reread_gap_s=float(
            os.environ.get("DETENT_REREAD_GAP_S", "0")
        ),
        probe_deadline_s=5.0,
    )


def main() -> None:
    assert_arming_sane()
    dsn = os.environ["DETENT_DSN"]
    refdest_url = os.environ["DETENT_REFDEST_URL"]
    declaration = load_declaration(declarations_dir() / "refdest-c2.capability.json")
    adapter = RefdestAdapter("refdest-c2", declaration, base_url=refdest_url)
    adapters = {"refdest-c2": adapter}

    ledger = Ledger(dsn)
    if not ledger.acquire_writer_lock():
        print("REFUSED writer lock held by another process", flush=True)
        sys.exit(3)

    config = _config()
    resolution_config = ResolutionConfig(
        auto_redispatch_effect_types=frozenset(
            t
            for t in os.environ.get("DETENT_AUTO_REDISPATCH_TYPES", "").split(",")
            if t
        ),
        reconcile=config,
    )
    recovery = run_recovery(
        ledger, adapters, config=config, resolution_config=resolution_config
    )
    print(
        "RECOVERY DONE "
        + json.dumps(
            {
                "scanned": recovery.scanned,
                "adjudicated": recovery.adjudicated,
                "parked": recovery.parked,
                "drained": recovery.drained,
            }
        ),
        flush=True,
    )
    print("READY", flush=True)

    from detent.dispatcher import dispatch

    for line in sys.stdin:
        line = line.strip()
        if not line:
            continue
        verb, _, rest = line.partition(" ")
        try:
            result: dict[str, Any]
            if verb == "REGISTER":
                reg = ledger.register_intent(
                    json.loads(rest), adapter.declaration_digest()
                )
                result = asdict(reg)
            elif verb == "DISPATCH":
                report = dispatch(ledger, adapter, rest.strip())
                result = {
                    "outcome": report.outcome,
                    "lifecycle": report.lifecycle,
                    "transport_outcome": report.transport_outcome,
                    "destination_ref": report.destination_ref,
                    "deny_check": report.claim.deny_check,
                    "deny_evidence": report.claim.deny_evidence,
                    "decision_id": report.claim.decision_id,
                }
            elif verb == "RECONCILE":
                rep = reconcile_effect(
                    ledger, adapter, rest.strip(), config=config
                )
                result = {
                    "queried": rep.queried,
                    "settled": rep.settled,
                    "still_ambiguous": rep.still_ambiguous,
                    "findings": rep.findings,
                }
            elif verb == "SWEEP":
                frm, _, to = rest.partition(" ")
                sw = run_sweep(ledger, adapter, frm.strip(), to.strip())
                result = {
                    "listed": sw.listed,
                    "matched": sw.matched,
                    "new_findings": sw.new_findings,
                    "known_findings": sw.known_findings,
                }
            elif verb == "EXIT":
                break
            else:
                result = {"error": f"unknown verb {verb}"}
            print("RESULT " + json.dumps(result, default=str), flush=True)
        except DetentError as err:
            print("RESULT " + json.dumps(err.to_envelope()), flush=True)


if __name__ == "__main__":
    main()
