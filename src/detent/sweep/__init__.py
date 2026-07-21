"""Orphan sweep (RFC-002 §7.2; RFC-001 §6).

Only where the declaration says ``list_queryable: true`` (typed refusal
otherwise — never a silently-empty result). Match order: stamped client
reference → receipt destination_ref → declared queryable keys, PLUS the
open-attempt guard: a listed effect matching an open attempt's operation_id is
a dispatch in flight — recorded as a sighting, never a finding. ORPHANED
emission requires unmatched sightings in ≥2 distinct runs, re-checked at
emission; idempotent via the partial unique index on
``(adapter_id, destination_ref)``.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

import psycopg

from detent.adapters.base import Adapter
from detent.errors import CapabilityUnsupported
from detent.identity import canonical_digest
from detent.ledger import Ledger
from detent.testhooks import crashpoint, syncpoint

__all__ = ["SweepReport", "sweep"]


@dataclass(slots=True)
class SweepReport:
    adapter_id: str = ""
    listed: int = 0
    matched: int = 0
    known_findings: int = 0
    new_findings: list[int] = field(default_factory=list)
    run_id: int = 0


def sweep(
    ledger: Ledger,
    adapter: Adapter,
    window_from: str,
    window_to: str,
    *,
    min_runs_for_orphan: int = 2,
) -> SweepReport:
    declaration = adapter.declare()
    if not declaration["list_queryable"]:
        raise CapabilityUnsupported(
            f"adapter {adapter.adapter_id}: sweep requires list_queryable=true "
            "(the declaration is enforced, not decorative)"
        )
    report = SweepReport(adapter_id=adapter.adapter_id)
    effects = adapter.list_effects(window_from, window_to)
    report.listed = len(effects)

    sightings: list[dict[str, Any]] = []
    unmatched: list[dict[str, Any]] = []
    for effect in effects:
        match_path, matched_effect = _match(ledger, effect)
        if matched_effect is not None:
            report.matched += 1
        sighting = {
            "destination_ref": effect["destination_ref"],
            "payload_digest": canonical_digest(effect),
            "matched_effect": matched_effect,
            "match_path": match_path,
        }
        sightings.append(sighting)
        if matched_effect is None:
            unmatched.append(sighting)

    report.run_id = ledger.record_sweep_run(
        adapter.adapter_id, window_from, window_to, report.listed, report.matched,
        sightings,
    )

    syncpoint("sweep.pre_finding")
    crashpoint("sweep.pre_finding")

    for sighting in unmatched:
        ref = sighting["destination_ref"]
        prior_runs = ledger.query(
            """
            SELECT count(DISTINCT run_id) AS n FROM sweep_sightings
            WHERE adapter_id = %s AND destination_ref = %s
              AND matched_effect IS NULL
            """,
            (adapter.adapter_id, ref),
        )
        if int(prior_runs[0]["n"]) < min_runs_for_orphan:
            continue  # two-pass rule: absorb listing lag + in-flight dispatches
        # Re-check at emission: the match state may have changed since listing.
        listed_effect = next(
            (e for e in effects if e["destination_ref"] == ref), None
        )
        if listed_effect is not None:
            _, matched_now = _match(ledger, listed_effect)
            if matched_now is not None:
                continue
        try:
            finding_id = ledger.attach_finding(
                None,
                adapter.adapter_id,
                "ORPHANED",
                {
                    "payload_digest": sighting["payload_digest"],
                    "window": {"from": window_from, "to": window_to},
                    "failed_match_paths": ["client_ref", "destination_ref"],
                    "runs_sighted": int(prior_runs[0]["n"]),
                },
                destination_ref=ref,
                created_by="sweep",
            )
            report.new_findings.append(finding_id)
        except psycopg.errors.UniqueViolation:
            # Already recorded by an earlier overlapping sweep — idempotent.
            report.known_findings += 1
        except Exception as err:  # translated typed errors
            if "duplicate key" in str(err):
                report.known_findings += 1
            else:
                raise
    return report


def _match(
    ledger: Ledger, effect: dict[str, Any]
) -> tuple[str | None, str | None]:
    """RFC-001 §6 match order. Path 1 (stamped client reference) also IS the
    open-attempt guard: an in-flight dispatch has its execution row (and open
    attempt) before any receipt exists, so its stamped operation_id matches."""
    client_ref = effect.get("client_ref")
    if client_ref:
        rows = ledger.query(
            "SELECT effect_id FROM effect_executions WHERE operation_id = %s",
            (client_ref,),
        )
        if rows:
            return ("client_ref", rows[0]["effect_id"])
    destination_ref = effect.get("destination_ref")
    if destination_ref:
        rows = ledger.query(
            """
            SELECT e.effect_id FROM dispatch_receipts r
            JOIN dispatch_attempts a USING (attempt_id)
            JOIN effect_executions e USING (execution_id)
            WHERE r.destination_ref = %s
            """,
            (destination_ref,),
        )
        if rows:
            return ("destination_ref", rows[0]["effect_id"])
    # Path 3 (declared queryable keys from stable_ids) has no derivable keys
    # for the refdest profile; real adapters add it at M4.
    return (None, None)
