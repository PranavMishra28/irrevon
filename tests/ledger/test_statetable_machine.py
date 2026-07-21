"""Model-level stateful property machine (testing.md §4.3, generative leg).

Conformance: master doc §12.1 row 3 (M3) — a Hypothesis RuleBasedStateMachine
drives an in-memory ledger model through the public operation shapes with the
auditor's legality predicate as the standing invariant. The DB-backed exhaustive
matrix lives in tests/integration/; this machine hunts for SEQUENCES of
operations that reach an illegal composite state. Oracle: the explicit fixture
table (fixtures/lifecycle-matrix.json) — not the statetable module under test.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from hypothesis import strategies as st
from hypothesis.stateful import RuleBasedStateMachine, invariant, precondition, rule

from detent.statetable import (
    CLASSIFICATIONS,
    LIFECYCLE_EDGES,
    LIFECYCLE_STATES,
    RESOLUTION_ACTIONS,
    TERMINAL_STATES,
    is_legal_attachment,
    is_legal_edge,
    is_legal_resolution,
)

_FIXTURE = json.loads(
    (
        Path(__file__).parent.parent
        / "integration"
        / "fixtures"
        / "lifecycle-matrix.json"
    ).read_text()
)
_FIXTURE_LEGAL_PAIRS = {
    (None if k.split("->")[0] == "GENESIS" else k.split("->")[0], k.split("->")[1])
    for k, v in _FIXTURE["cells"].items()
    if v == "LEGAL"
}

_EDGE_LIST = sorted(LIFECYCLE_EDGES, key=lambda e: (str(e[0]), e[1], e[2], e[3]))


class LedgerModel(RuleBasedStateMachine):
    """In-memory mirror of one effect's executions/findings, driven by the
    operation shapes the real ledger exposes."""

    def __init__(self) -> None:
        super().__init__()
        self.executions: list[str] = []  # frontier per execution (index = step)
        self.findings: list[dict[str, Any]] = []

    # ── operations ────────────────────────────────────────────────────────────

    @rule()
    def open_execution(self) -> None:
        # Mirrors ledger_open_execution: first execution via register; later
        # ones only when the latest frontier is SETTLED_FAILED (§5.3).
        if self.executions and self.executions[-1] != "SETTLED_FAILED":
            return  # precondition violated: the real function raises DT005
        self.executions.append("PERSISTED")

    @precondition(lambda self: bool(self.executions))
    @rule(data=st.data())
    def attempt_transition(self, data: st.DataObject) -> None:
        idx = data.draw(
            st.integers(min_value=0, max_value=len(self.executions) - 1)
        )
        frontier = self.executions[idx]
        to_state = data.draw(st.sampled_from(LIFECYCLE_STATES))
        cause, actor = data.draw(
            st.sampled_from([(e[2], e[3]) for e in _EDGE_LIST])
        )
        if is_legal_edge(frontier, to_state, cause, actor):
            # Only the LATEST execution may move in the real ledger flows the
            # machine models; earlier executions are terminal by construction.
            if idx == len(self.executions) - 1:
                self.executions[idx] = to_state
        # illegal edge ⇒ the locked function raises, nothing changes.

    @precondition(lambda self: bool(self.executions))
    @rule(data=st.data())
    def attempt_attach(self, data: st.DataObject) -> None:
        classification = data.draw(st.sampled_from(CLASSIFICATIONS))
        if classification == "ORPHANED":
            return  # destination-keyed; never attaches to this effect
        frontier = self.executions[-1]
        if is_legal_attachment(frontier, classification):
            finding = {"classification": classification, "status": "OPEN"}
            if classification == "CONFIRMED_UNIQUE":
                finding["status"] = "CLOSED"  # auto-resolve + close (§3.3)
            self.findings.append(finding)

    @precondition(lambda self: bool(self.findings))
    @rule(data=st.data())
    def attempt_resolve(self, data: st.DataObject) -> None:
        finding = data.draw(st.sampled_from(self.findings))
        to_status = data.draw(
            st.sampled_from((*RESOLUTION_ACTIONS, "CLOSED"))
        )
        if is_legal_resolution(finding["classification"], finding["status"], to_status):
            finding["status"] = to_status

    # ── the auditor's legality predicate as the standing invariant ────────────

    @invariant()
    def all_frontiers_are_reachable_states(self) -> None:
        for frontier in self.executions:
            assert frontier in LIFECYCLE_STATES

    @invariant()
    def non_latest_executions_are_terminal(self) -> None:
        for frontier in self.executions[:-1]:
            assert frontier in TERMINAL_STATES or frontier == "SETTLED_FAILED"

    @invariant()
    def findings_only_on_legal_frontiers(self) -> None:
        for finding in self.findings:
            assert any(
                is_legal_attachment(frontier, finding["classification"])
                for frontier in self.executions
            )

    @invariant()
    def duplicate_findings_never_redispatched(self) -> None:
        for finding in self.findings:
            if finding["classification"] == "DUPLICATE":
                assert finding["status"] != "REDISPATCHED"

    @invariant()
    def statetable_matches_fixture_oracle(self) -> None:
        # Generated-from discipline inside the machine: the module's legal set
        # must equal the human-reviewed fixture at every step.
        assert {(f, t) for (f, t, _c, _a) in LIFECYCLE_EDGES} == _FIXTURE_LEGAL_PAIRS


TestLedgerModel = LedgerModel.TestCase


def test_legal_pairs_match_fixture() -> None:
    assert {(f, t) for (f, t, _c, _a) in LIFECYCLE_EDGES} == _FIXTURE_LEGAL_PAIRS


def test_terminality_is_ratified() -> None:
    for from_state, _to, _c, _a in LIFECYCLE_EDGES:
        assert from_state not in TERMINAL_STATES, "no edge may leave a terminal state"


def test_resolution_never_leaves_closed() -> None:
    for classification in CLASSIFICATIONS:
        for to_status in (*RESOLUTION_ACTIONS, "CLOSED", "OPEN"):
            assert not is_legal_resolution(classification, "CLOSED", to_status)
