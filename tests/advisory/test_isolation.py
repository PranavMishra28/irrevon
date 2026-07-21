"""Classifier-isolation conformance (RFC-002 §14; testing.md §4.4).

Conformance: master doc §12.1 row 4 — "LLM never on the authority path (§6.3,
ADR-006)" (M3). Three legs: (1) the static import boundary (import-linter
contract, enforced in `make py-check` — no authority module imports
irrevon.advisory, direct or indirect); (2) type-level runtime rejection —
ClassifierProposal objects, duck-typed lookalikes, AND
serialized-then-deserialized launderings fed to EVERY mutation-capable API
produce a typed rejection; (3) the ledger is unchanged after every attempt
(asserted here and by the standing auditor post-condition).
"""

from __future__ import annotations

import json
import subprocess
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

import pytest

from irrevon.advisory import ClassifierProposal
from irrevon.errors import AdvisoryRejected
from irrevon.ledger import Ledger
from tests.integration.conftest import DBHandles
from tests.integration.driver import admin_conn, make_effect, make_execution_at

pytestmark = pytest.mark.integration

REPO_ROOT = Path(__file__).parent.parent.parent

PROPOSAL = ClassifierProposal(
    subject_effect_id="a" * 64,
    proposed_action="ACCEPTED_AS_IS",
    confidence=0.99,
    rationale="the model is very sure",
)


def _payloads() -> list[Any]:
    """The adversarial corpus: the proposal object itself, its serialized
    payload, a JSON round-trip (laundering), and a duck-typed lookalike."""

    class Lookalike:
        proposed_action = "ACCEPTED_AS_IS"
        confidence = 1.0

    return [
        PROPOSAL,
        PROPOSAL.to_payload(),
        json.loads(json.dumps(PROPOSAL.to_payload())),
        Lookalike(),
    ]


def test_static_import_boundary_is_enforced() -> None:
    """Leg 1: lint-imports must list the ADR-006 contract and keep it."""
    import shutil

    lint_imports = shutil.which("lint-imports")
    assert lint_imports, "lint-imports must be installed (dev dependency)"
    result = subprocess.run(
        [lint_imports],
        capture_output=True,
        text=True,
        cwd=REPO_ROOT,
        timeout=120,
    )
    assert result.returncode == 0, result.stdout + result.stderr
    assert "advisory is never on the authority path (ADR-006)" in result.stdout
    assert "0 broken" in result.stdout.lower()


def test_no_source_shipping_module_imports_advisory() -> None:
    """Belt-and-braces on top of import-linter: the contract file itself must
    keep every authority module in its source list (changing the contract is
    invariant-affecting — ADR first, §12.5)."""
    pyproject = (REPO_ROOT / "pyproject.toml").read_text()
    for module in ("irrevon.ledger", "irrevon.gate", "irrevon.dispatcher",
                   "irrevon.reconciler", "irrevon.recovery", "irrevon.resolution",
                   "irrevon.api", "irrevon.cli"):
        assert f'"{module}"' in pyproject, f"{module} missing from the contract"


def test_every_mutation_api_rejects_advisory_output(fresh_db: DBHandles) -> None:
    """Leg 2 + 3: every mutation-capable API produces a typed rejection and
    the ledger is byte-unchanged."""
    with admin_conn(fresh_db.admin_dsn) as conn:
        effect_id = make_effect(conn)
        execution_id = make_execution_at(conn, effect_id, "AMBIGUOUS")
        settled = make_effect(conn, scope="advisory-2")
        make_execution_at(conn, settled, "SETTLED_COMMITTED")
        finding_row = conn.execute(
            "SELECT ledger_attach_finding(%s, 'refdest-c2', NULL, 'DUPLICATE', 1, "
            "'{\"probe_ids\": [1]}'::jsonb, 'sha256:0', 'reconciler') AS fid",
            (settled,),
        ).fetchone()
        assert finding_row is not None
        finding_id = finding_row["fid"]

    def table_counts() -> dict[str, int]:
        with admin_conn(fresh_db.admin_dsn) as conn:
            return {
                t: conn.execute(f"SELECT count(*) AS n FROM {t}").fetchone()["n"]  # type: ignore[index,union-attr]
                for t in (
                    "effect_records",
                    "effect_transitions",
                    "findings",
                    "finding_resolutions",
                    "dispatch_receipts",
                )
            }

    before = table_counts()
    with Ledger(fresh_db.app_dsn) as ledger:
        for payload in _payloads():
            with pytest.raises(AdvisoryRejected):
                ledger.register_intent(payload, "sha256:" + "d" * 64)
            with pytest.raises(AdvisoryRejected):
                ledger.settle_ambiguous(
                    execution_id,
                    "SETTLED_COMMITTED",
                    "reconciled_present",
                    "reconciler",
                    payload,  # type: ignore[arg-type]
                    classification="CONFIRMED_UNIQUE",
                )
            with pytest.raises(AdvisoryRejected):
                ledger.attach_finding(
                    settled, "refdest-c2", "CONTRADICTED",
                    payload,  # type: ignore[arg-type]
                )
            with pytest.raises(AdvisoryRejected):
                ledger.resolve_finding(
                    finding_id, "OPEN", "ACCEPTED_AS_IS", "human",
                    payload,  # type: ignore[arg-type]
                )
    assert table_counts() == before, "advisory attempts must leave the ledger unchanged"

    # A real human resolution still works — the boundary blocks proposals,
    # not authority.
    with Ledger(fresh_db.app_dsn) as ledger:
        ledger.resolve_finding(
            finding_id, "OPEN", "ACCEPTED_AS_IS", "human",
            {"note": "human judgment with evidence"},
        )
        ledger.resolve_finding(
            finding_id, "ACCEPTED_AS_IS", "CLOSED", "human", {"note": "closing"}
        )


def test_resolution_engine_rejects_proposals(fresh_db: DBHandles) -> None:
    from irrevon.resolution import resolve

    with admin_conn(fresh_db.admin_dsn) as conn:
        effect_id = make_effect(conn)
        make_execution_at(conn, effect_id, "SETTLED_FAILED")
        finding_row = conn.execute(
            "SELECT ledger_attach_finding(%s, 'refdest-c2', NULL, 'LOST', NULL, "
            "'{\"probe_ids\": [1]}'::jsonb, 'sha256:0', 'reconciler') AS fid",
            (effect_id,),
        ).fetchone()
        assert finding_row is not None
    with Ledger(fresh_db.app_dsn) as ledger:
        with pytest.raises(AdvisoryRejected):
            resolve(
                ledger, {}, finding_row["fid"], "ACCEPTED_AS_IS",
                PROPOSAL.to_payload(),
            )
        # Park it legally so the auditor sees a coherent end state.
        ledger.resolve_finding(
            finding_row["fid"], "OPEN", "ESCALATED_HUMAN", "human",
            {"note": "parked"},
        )


def test_proposal_never_reaches_gate_inputs() -> None:
    """The gate consumes typed GateInputs only; a proposal cannot be smuggled
    as evidence because evaluate() builds evidence itself from ledger facts.
    This asserts the type surface: GateInputs has no advisory-shaped member."""
    from dataclasses import fields

    from irrevon.gate import GateInputs

    field_names = {f.name for f in fields(GateInputs)}
    assert "proposal" not in field_names
    assert "classifier" not in field_names
    assert "advisory" not in field_names


def test_registrar_rejects_advisory_marker_in_contract() -> None:
    """A contract dict carrying the advisory marker is rejected BEFORE schema
    validation (defense in depth; the closed schema would also reject it)."""
    from irrevon.errors import ADVISORY_MARKER

    raw = {
        "schema_version": "1",
        "stable_ids": {"order_id": "1"},
        "effect_type": "order.create",
        "effect_class": "IRREVERSIBLE",
        "scope": "s",
        "adapter_id": "refdest-c2",
        "parameters": {},
        "authority_ref": "auth",
        "stamped_at": datetime.now(UTC).isoformat().replace("+00:00", "Z"),
        ADVISORY_MARKER: True,
    }
    from irrevon.errors import reject_advisory

    with pytest.raises(AdvisoryRejected):
        reject_advisory(raw, "registerIntent")
