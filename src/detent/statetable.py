"""The canonical state tables — encoded verbatim from RFC-002 §3.

RFC-002 §3 is THE ratified state model; this module is its single in-code
encoding. The SQL edge tables seeded by migrations, the SDK enums, and the M3
matrix tests are all validated against THIS module (tests cross-check the SQL
seed rows and the record-schema enums against these constants — generated-from,
never hand-copied; ADR-0019 item 4). Changing anything here is an amendment to
the ratified table, not a local fix (T-102 human-review trigger).

Pure module: constants and predicates only — importable from every module
without dragging in SQL or I/O.
"""

from __future__ import annotations

from typing import Final

# ── Dimension A: lifecycle states ─────────────────────────────────────────────

LIFECYCLE_STATES: Final = (
    "INTENDED",
    "PERSISTED",
    "DISPATCHED",
    "SETTLED_COMMITTED",
    "SETTLED_FAILED",
    "AMBIGUOUS",
    "CANCELLED",
)

TERMINAL_STATES: Final = ("SETTLED_COMMITTED", "SETTLED_FAILED", "CANCELLED")

TRANSITION_CAUSES: Final = (
    "register",
    "durable_write",
    "branch_cancelled",
    "gate_allow",
    "receipt_ok",
    "receipt_failed",
    "receipt_timeout",
    "receipt_lost",
    "reconciled_present",
    "reconciled_absent",
    "replay_ok",
    "replay_failed",
)

TRANSITION_ACTORS: Final = (
    "registrar",
    "gate",
    "dispatcher",
    "reconciler",
    "recovery",
    "human",
)

# RFC-002 §3.1 — every (from, to, cause, actor) tuple not listed is illegal.
# ``None`` from-state is genesis. Cause and actor are part of edge legality.
LIFECYCLE_EDGES: Final[frozenset[tuple[str | None, str, str, str]]] = frozenset(
    {
        (None, "INTENDED", "register", "registrar"),
        ("INTENDED", "PERSISTED", "durable_write", "registrar"),
        ("INTENDED", "CANCELLED", "branch_cancelled", "registrar"),
        ("PERSISTED", "DISPATCHED", "gate_allow", "gate"),
        ("PERSISTED", "CANCELLED", "branch_cancelled", "gate"),
        ("PERSISTED", "CANCELLED", "branch_cancelled", "human"),
        ("DISPATCHED", "SETTLED_COMMITTED", "receipt_ok", "dispatcher"),
        ("DISPATCHED", "SETTLED_FAILED", "receipt_failed", "dispatcher"),
        ("DISPATCHED", "AMBIGUOUS", "receipt_timeout", "dispatcher"),
        ("DISPATCHED", "AMBIGUOUS", "receipt_timeout", "recovery"),
        ("DISPATCHED", "AMBIGUOUS", "receipt_lost", "dispatcher"),
        ("DISPATCHED", "AMBIGUOUS", "receipt_lost", "recovery"),
        ("AMBIGUOUS", "SETTLED_COMMITTED", "reconciled_present", "reconciler"),
        ("AMBIGUOUS", "SETTLED_COMMITTED", "reconciled_present", "recovery"),
        ("AMBIGUOUS", "SETTLED_COMMITTED", "reconciled_present", "human"),
        ("AMBIGUOUS", "SETTLED_COMMITTED", "replay_ok", "reconciler"),
        ("AMBIGUOUS", "SETTLED_COMMITTED", "replay_ok", "recovery"),
        ("AMBIGUOUS", "SETTLED_COMMITTED", "replay_ok", "human"),
        ("AMBIGUOUS", "SETTLED_FAILED", "reconciled_absent", "reconciler"),
        ("AMBIGUOUS", "SETTLED_FAILED", "reconciled_absent", "recovery"),
        ("AMBIGUOUS", "SETTLED_FAILED", "reconciled_absent", "human"),
        ("AMBIGUOUS", "SETTLED_FAILED", "replay_failed", "reconciler"),
        ("AMBIGUOUS", "SETTLED_FAILED", "replay_failed", "recovery"),
        ("AMBIGUOUS", "SETTLED_FAILED", "replay_failed", "human"),
    }
)

LEGAL_STATE_PAIRS: Final[frozenset[tuple[str | None, str]]] = frozenset(
    (f, t) for (f, t, _c, _a) in LIFECYCLE_EDGES
)


def is_legal_edge(
    from_state: str | None, to_state: str, cause: str, actor: str
) -> bool:
    return (from_state, to_state, cause, actor) in LIFECYCLE_EDGES


# ── Dimension B: classifications (findings cite effects) ─────────────────────

CLASSIFICATIONS: Final = (
    "CONFIRMED_UNIQUE",
    "DUPLICATE",
    "LOST",
    "ORPHANED",
    "CONTRADICTED",
)

FINDING_CREATORS: Final = ("reconciler", "recovery", "sweep", "human")

# RFC-002 §3.2 — legal (frontier, classification) attachment cells. UNRECONCILED
# is the absence of findings, not a finding. ORPHANED is destination-keyed only
# (effect_id IS NULL) and never attaches to a record — it appears in the
# CLASSIFICATIONS enum so tests enumerate it as illegal everywhere.
LEGAL_ATTACHMENTS: Final[frozenset[tuple[str, str]]] = frozenset(
    {
        ("SETTLED_COMMITTED", "CONFIRMED_UNIQUE"),
        ("SETTLED_COMMITTED", "DUPLICATE"),
        ("SETTLED_COMMITTED", "CONTRADICTED"),
        ("SETTLED_FAILED", "DUPLICATE"),
        ("SETTLED_FAILED", "LOST"),
        ("SETTLED_FAILED", "CONTRADICTED"),
    }
)


def is_legal_attachment(frontier: str, classification: str) -> bool:
    return (frontier, classification) in LEGAL_ATTACHMENTS


# ── Dimension C: resolution legality (per finding) ────────────────────────────

RESOLUTION_STATUSES: Final = (
    "OPEN",
    "COMPENSATED",
    "REDISPATCHED",
    "ACCEPTED_AS_IS",
    "ESCALATED_HUMAN",
    "CLOSED",
)

RESOLUTION_ACTIONS: Final = (
    "COMPENSATED",
    "REDISPATCHED",
    "ACCEPTED_AS_IS",
    "ESCALATED_HUMAN",
)

RESOLUTION_ACTORS: Final = ("human", "policy_auto", "recovery", "system")

# RFC-002 §3.3 — classification × action legality. REDISPATCHED on a DUPLICATE
# is ILLEGAL, always: redispatching a duplicate manufactures more.
LEGAL_ACTIONS: Final[frozenset[tuple[str, str]]] = frozenset(
    {
        ("CONFIRMED_UNIQUE", "ACCEPTED_AS_IS"),  # auto: system actor, settle txn
        ("DUPLICATE", "COMPENSATED"),
        ("DUPLICATE", "ACCEPTED_AS_IS"),
        ("DUPLICATE", "ESCALATED_HUMAN"),
        ("LOST", "REDISPATCHED"),
        ("LOST", "ACCEPTED_AS_IS"),
        ("LOST", "ESCALATED_HUMAN"),
        ("ORPHANED", "COMPENSATED"),
        ("ORPHANED", "ACCEPTED_AS_IS"),
        ("ORPHANED", "ESCALATED_HUMAN"),
        ("CONTRADICTED", "COMPENSATED"),
        ("CONTRADICTED", "ACCEPTED_AS_IS"),
        ("CONTRADICTED", "ESCALATED_HUMAN"),  # default route: Sev-2 signal
    }
)

# Status chain: OPEN → action; ESCALATED_HUMAN → {COMPENSATED, REDISPATCHED,
# ACCEPTED_AS_IS}; action status → CLOSED.
LEGAL_STATUS_EDGES: Final[frozenset[tuple[str, str]]] = frozenset(
    {("OPEN", a) for a in RESOLUTION_ACTIONS}
    | {
        ("ESCALATED_HUMAN", "COMPENSATED"),
        ("ESCALATED_HUMAN", "REDISPATCHED"),
        ("ESCALATED_HUMAN", "ACCEPTED_AS_IS"),
    }
    | {(a, "CLOSED") for a in ("COMPENSATED", "REDISPATCHED", "ACCEPTED_AS_IS")}
)


def is_legal_resolution(
    classification: str, from_status: str, to_status: str
) -> bool:
    """A resolution edge is legal when the status chain permits it AND (for
    action-entering edges) the classification × action cell is legal."""
    if (from_status, to_status) not in LEGAL_STATUS_EDGES:
        return False
    if to_status in RESOLUTION_ACTIONS:
        return (classification, to_status) in LEGAL_ACTIONS
    return True


# ── Receipts / transport taxonomy (RFC-002 §10) ──────────────────────────────

TRANSPORT_OUTCOMES: Final = ("OK", "FAILED", "TIMEOUT", "LOST")
FAILURE_KINDS: Final = ("TERMINAL", "RETRYABLE")
RECEIPT_RECORDERS: Final = ("dispatcher", "reconciler", "recovery")
ATTEMPT_KINDS: Final = ("primary", "recovery_redispatch", "c1_replay_probe")
EXECUTION_OPENERS: Final = ("register", "retry_after_failure", "resolve_redispatch")
PROBE_KINDS: Final = ("reconcile_open", "audit", "sweep")
PROBE_RESULTS: Final = ("PRESENT", "ABSENT", "INDETERMINATE")
EFFECT_CLASSES: Final = ("IDEMPOTENT", "REVERSIBLE", "COMPENSABLE", "IRREVERSIBLE")
GATE_CHECKS: Final = ("deny_list", "authority", "branch_lineage", "dedup")
GATE_VARIANTS: Final = (
    "dispatch",
    "recovery_redispatch",
    "resolve_redispatch",
    "retry_after_failure",
)
