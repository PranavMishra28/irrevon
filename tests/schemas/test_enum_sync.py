"""Generated-from enforcement for the record schemas (ADR-0019 item 4 /
ADR-0021): every enum in the admitted schemas must equal the ratified state
table's encoding in irrevon.statetable — never hand-copied, never drifting."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from irrevon import statetable

SCHEMAS_DIR = Path(__file__).parent.parent.parent / "schemas"


def _load(name: str) -> dict[str, Any]:
    return json.loads((SCHEMAS_DIR / name).read_text(encoding="utf-8"))


def test_effect_record_lifecycle_enum() -> None:
    schema = _load("effect-record.schema.json")
    assert tuple(schema["properties"]["lifecycle"]["enum"]) == (
        statetable.LIFECYCLE_STATES
    )
    assert tuple(schema["properties"]["effect_class"]["enum"]) == (
        statetable.EFFECT_CLASSES
    )


def test_dispatch_receipt_enums() -> None:
    schema = _load("dispatch-receipt.schema.json")
    props = schema["properties"]
    assert tuple(props["transport_outcome"]["enum"]) == statetable.TRANSPORT_OUTCOMES
    assert tuple(props["failure_kind"]["enum"]) == statetable.FAILURE_KINDS
    assert tuple(props["kind"]["enum"]) == statetable.ATTEMPT_KINDS
    assert tuple(props["recorded_by"]["enum"]) == statetable.RECEIPT_RECORDERS


def test_reconciliation_finding_enums() -> None:
    schema = _load("reconciliation-finding.schema.json")
    props = schema["properties"]
    assert tuple(props["classification"]["enum"]) == statetable.CLASSIFICATIONS
    assert tuple(props["created_by"]["enum"]) == statetable.FINDING_CREATORS
    assert tuple(props["resolution"]["properties"]["status"]["enum"]) == (
        statetable.RESOLUTION_STATUSES
    )


def test_intent_contract_effect_class_enum() -> None:
    schema = _load("intent-contract.schema.json")
    assert tuple(schema["properties"]["effect_class"]["enum"]) == (
        statetable.EFFECT_CLASSES
    )
