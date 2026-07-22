"""Engine worker subprocess for the flagship demo (RFC-001 §3/§9.5).

`irrevon demo` orchestrates REAL processes: this worker boots the Engine (writer
lock → recovery → READY) against the demo database and reference destination,
then serves line commands on stdin. The demo's crash step is a genuine SIGKILL
of this process delivered by the orchestrator.

Protocol (stdout): "RECOVERY DONE <json>" · "READY" · "RESULT <json>".
Commands (stdin): REGISTER <json> | DISPATCH <id> | RECONCILE <id> | EXIT.
"""

from __future__ import annotations

import json
import os
import sys
from dataclasses import asdict
from typing import Any

from irrevon.adapters.base import declarations_dir, load_declaration
from irrevon.adapters.refdest import RefdestAdapter
from irrevon.api import Engine
from irrevon.errors import IrrevonError
from irrevon.reconciler import ReconcileConfig
from irrevon.testhooks import assert_arming_sane


def main() -> None:
    assert_arming_sane()
    dsn = os.environ["IRREVON_DSN"]
    refdest_url = os.environ["IRREVON_REFDEST_URL"]
    declaration = load_declaration(declarations_dir() / "refdest-c2.capability.json")
    adapter = RefdestAdapter("refdest-c2", declaration, base_url=refdest_url)
    config = ReconcileConfig(
        absence_reread_gap_s=float(os.environ.get("IRREVON_REREAD_GAP_S", "0")),
        probe_deadline_s=5.0,
    )
    try:
        engine = Engine(dsn, {"refdest-c2": adapter}, reconcile_config=config)
        recovery = engine.boot()
    except IrrevonError as err:
        print("REFUSED " + json.dumps(err.to_envelope()), flush=True)
        sys.exit(3)
    print(
        "RECOVERY DONE "
        + json.dumps(
            {"scanned": recovery.scanned, "adjudicated": recovery.adjudicated}
        ),
        flush=True,
    )
    print("READY", flush=True)

    for line in sys.stdin:
        line = line.strip()
        if not line:
            continue
        verb, _, rest = line.partition(" ")
        try:
            result: dict[str, Any]
            if verb == "REGISTER":
                result = asdict(engine.register_intent(json.loads(rest)))
            elif verb == "DISPATCH":
                report = engine.dispatch(rest.strip())
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
                rep = engine.reconcile(rest.strip())
                result = {
                    "settled": rep.settled,
                    "still_ambiguous": rep.still_ambiguous,
                    "findings": rep.findings,
                }
            elif verb == "EXIT":
                break
            else:
                result = {"error": f"unknown verb {verb}"}
            print("RESULT " + json.dumps(result, default=str), flush=True)
        except IrrevonError as err:
            print("RESULT " + json.dumps(err.to_envelope()), flush=True)
    engine.close()


if __name__ == "__main__":
    main()
