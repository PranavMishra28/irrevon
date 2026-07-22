"""The ledger auditor — cross-cutting post-condition (testing.md §3.5).

A pure read-only function ``audit(dsn) -> list[Violation]`` run after every
integration/fault/E2E test, so the global invariants are asserted thousands of
times per run, not once:

1. append-only enforcement present (no-rewrite triggers on every fact table);
2. state legality: every transition edge is in the ratified §3.1 table; every
   execution history is a contiguous single chain from genesis; nothing follows
   a terminal state (per-execution terminality);
3. classification legality: every record-keyed finding is justified by an
   execution whose frontier makes the (frontier, classification) cell legal
   (§3.2); ORPHANED findings never reference a record; DUPLICATE carries
   ``excess_effect_count`` ≥ 1;
4. evidence completeness: every AMBIGUOUS entry has a TIMEOUT/LOST receipt on
   that execution; every exit from AMBIGUOUS carries justification evidence
   (probe / receipt / human reference);
5. resolution legality: every finding's resolution chain is legal per §3.3;
6. gate discipline: every DISPATCHED entry cites an ALLOW gate decision and has
   a claimed attempt row.

The auditor is itself unit-tested against hand-built corrupt ledgers (it must
FAIL on each seeded violation) so it cannot rot into a rubber stamp.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from irrevon.ledger.db import connect
from irrevon.statetable import (
    LIFECYCLE_EDGES,
    TERMINAL_STATES,
    is_legal_attachment,
    is_legal_resolution,
)

__all__ = ["Violation", "audit"]

_FACT_TABLES = (
    "effect_records",
    "parameter_variants",
    "effect_executions",
    "effect_transitions",
    "scope_slots",
    "gate_decisions",
    "dispatch_attempts",
    "dispatch_receipts",
    "late_responses",
    "status_probes",
    "findings",
    "finding_resolutions",
    "authorities",
    "effect_authorities",
    "branch_cancellations",
    "deny_entries",
    "deny_lifts",
    "sweep_runs",
    "sweep_sightings",
    "recovery_runs",
)

_AMBIGUOUS_EXIT_JUSTIFICATION_KEYS = frozenset(
    {"probe_ids", "receipt_id", "human", "note"}
)


@dataclass(frozen=True, slots=True)
class Violation:
    rule: str
    detail: str


def audit(dsn: str) -> list[Violation]:
    violations: list[Violation] = []
    with connect(dsn) as conn:
        rows = conn.execute
        # ── 1. append-only triggers present ───────────────────────────────────
        trigger_rows = rows(
            """
            SELECT c.relname FROM pg_trigger t
            JOIN pg_class c ON c.oid = t.tgrelid
            WHERE NOT t.tgisinternal AND t.tgname LIKE '%_append_only'
            """
        ).fetchall()
        present = {r["relname"] for r in trigger_rows}
        for table in _FACT_TABLES:
            if table not in present:
                violations.append(
                    Violation("append_only", f"table {table} lacks its no-rewrite trigger")
                )

        # ── 2. transition histories: legal edges, contiguity, terminality ─────
        transitions = rows(
            """
            SELECT execution_id, transition_seq, from_state, to_state, cause, actor,
                   evidence
            FROM effect_transitions ORDER BY execution_id, transition_seq
            """
        ).fetchall()
        by_execution: dict[int, list[dict[str, Any]]] = {}
        for t in transitions:
            by_execution.setdefault(t["execution_id"], []).append(t)
        for execution_id, chain in by_execution.items():
            prev_state: str | None = None
            terminal_seen = False
            for i, t in enumerate(chain):
                edge = (t["from_state"], t["to_state"], t["cause"], t["actor"])
                if edge not in LIFECYCLE_EDGES:
                    violations.append(
                        Violation(
                            "state_legality",
                            f"execution {execution_id} seq {t['transition_seq']}: "
                            f"illegal edge {edge}",
                        )
                    )
                if i == 0 and t["from_state"] is not None:
                    violations.append(
                        Violation(
                            "contiguity",
                            f"execution {execution_id}: first transition is not genesis",
                        )
                    )
                if i > 0 and t["from_state"] != prev_state:
                    violations.append(
                        Violation(
                            "contiguity",
                            f"execution {execution_id} seq {t['transition_seq']}: "
                            f"from_state {t['from_state']} != prior frontier {prev_state}",
                        )
                    )
                if terminal_seen:
                    violations.append(
                        Violation(
                            "terminality",
                            f"execution {execution_id} seq {t['transition_seq']}: "
                            "transition after a terminal state",
                        )
                    )
                prev_state = t["to_state"]
                terminal_seen = terminal_seen or t["to_state"] in TERMINAL_STATES

        # ── 3. classification legality ────────────────────────────────────────
        findings = rows(
            """
            SELECT f.finding_id, f.effect_id, f.classification, f.excess_effect_count,
                   f.destination_ref
            FROM findings f
            """
        ).fetchall()
        frontier_rows = rows(
            "SELECT effect_id, execution_id, frontier FROM execution_frontiers"
        ).fetchall()
        frontiers_by_effect: dict[str, list[str]] = {}
        for r in frontier_rows:
            frontiers_by_effect.setdefault(r["effect_id"], []).append(r["frontier"])
        for f in findings:
            if f["classification"] == "ORPHANED":
                if f["effect_id"] is not None:
                    violations.append(
                        Violation(
                            "classification",
                            f"finding {f['finding_id']}: ORPHANED attached to a record",
                        )
                    )
                continue
            if f["effect_id"] is None:
                violations.append(
                    Violation(
                        "classification",
                        f"finding {f['finding_id']}: record-less non-ORPHANED finding",
                    )
                )
                continue
            legal = any(
                is_legal_attachment(frontier, f["classification"])
                for frontier in frontiers_by_effect.get(f["effect_id"], [])
            )
            if not legal:
                violations.append(
                    Violation(
                        "classification",
                        f"finding {f['finding_id']}: {f['classification']} on effect "
                        f"{f['effect_id']} with no execution in a legal frontier (§3.2)",
                    )
                )
            if f["classification"] == "DUPLICATE" and (
                f["excess_effect_count"] is None or f["excess_effect_count"] < 1
            ):
                violations.append(
                    Violation(
                        "classification",
                        f"finding {f['finding_id']}: DUPLICATE without excess count",
                    )
                )

        # ── 4. AMBIGUOUS evidence completeness ────────────────────────────────
        receipts_by_execution: dict[int, list[dict[str, Any]]] = {}
        for r in rows(
            """
            SELECT a.execution_id, rc.transport_outcome, rc.evidence
            FROM dispatch_receipts rc JOIN dispatch_attempts a USING (attempt_id)
            """
        ).fetchall():
            receipts_by_execution.setdefault(r["execution_id"], []).append(r)
        for execution_id, chain in by_execution.items():
            for t in chain:
                if t["to_state"] == "AMBIGUOUS":
                    justifying = [
                        r
                        for r in receipts_by_execution.get(execution_id, [])
                        if r["transport_outcome"] in ("TIMEOUT", "LOST")
                    ]
                    if not justifying:
                        violations.append(
                            Violation(
                                "ambiguous_evidence",
                                f"execution {execution_id}: AMBIGUOUS without a "
                                "TIMEOUT/LOST receipt",
                            )
                        )
                if t["from_state"] == "AMBIGUOUS":
                    evidence = t["evidence"] or {}
                    if not (
                        isinstance(evidence, dict)
                        and _AMBIGUOUS_EXIT_JUSTIFICATION_KEYS & evidence.keys()
                    ):
                        violations.append(
                            Violation(
                                "ambiguous_evidence",
                                f"execution {execution_id} seq {t['transition_seq']}: "
                                "exit from AMBIGUOUS without justification evidence",
                            )
                        )

        # ── 5. resolution legality ────────────────────────────────────────────
        resolutions = rows(
            """
            SELECT r.finding_id, r.resolution_seq, r.from_status, r.to_status,
                   f.classification
            FROM finding_resolutions r JOIN findings f USING (finding_id)
            ORDER BY r.finding_id, r.resolution_seq
            """
        ).fetchall()
        chains: dict[int, list[dict[str, Any]]] = {}
        for r in resolutions:
            chains.setdefault(r["finding_id"], []).append(r)
        for finding_id, chain in chains.items():
            current = "OPEN"
            for r in chain:
                if r["from_status"] != current:
                    violations.append(
                        Violation(
                            "resolution",
                            f"finding {finding_id} seq {r['resolution_seq']}: "
                            f"from_status {r['from_status']} != current {current}",
                        )
                    )
                if not is_legal_resolution(
                    r["classification"], r["from_status"], r["to_status"]
                ):
                    violations.append(
                        Violation(
                            "resolution",
                            f"finding {finding_id} seq {r['resolution_seq']}: illegal "
                            f"{r['from_status']} -> {r['to_status']} for "
                            f"{r['classification']} (§3.3)",
                        )
                    )
                current = r["to_status"]

        # ── 6. gate discipline on every DISPATCHED entry ──────────────────────
        allowed = {
            r["execution_id"]
            for r in rows(
                "SELECT execution_id FROM gate_decisions WHERE outcome = 'ALLOW'"
            ).fetchall()
        }
        attempted = {
            r["execution_id"]
            for r in rows("SELECT execution_id FROM dispatch_attempts").fetchall()
        }
        for execution_id, chain in by_execution.items():
            for t in chain:
                if t["to_state"] == "DISPATCHED":
                    if execution_id not in allowed:
                        violations.append(
                            Violation(
                                "gate",
                                f"execution {execution_id}: DISPATCHED without an "
                                "ALLOW gate decision",
                            )
                        )
                    if execution_id not in attempted:
                        violations.append(
                            Violation(
                                "gate",
                                f"execution {execution_id}: DISPATCHED without a "
                                "claimed attempt row",
                            )
                        )
    return violations
