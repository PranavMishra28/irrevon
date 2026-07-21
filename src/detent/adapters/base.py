"""Adapter protocol (ADR-005; adapters.md §1) — language-shaped encoding.

Contract highlights:

- ``dispatch`` executes exactly ONE wire attempt; the adapter never retries a
  dispatch internally (hidden retries would corrupt attempt accounting and, on
  C2, silently manufacture duplicates). Retry policy is the core's.
- Unknown or unrecognized destination outcomes map to LOST/TIMEOUT (→
  AMBIGUOUS), NEVER FAILED (RFC-002 §10). Only error shapes the capability
  declaration's citations prove side-effect-free may map to FAILED.
- ``status_query``/``dedup_check`` are authoritative reads; a failed query is
  INDETERMINATE, never coerced to ABSENT.
- Adapters are stateless between calls; all durable state is the ledger's.
"""

from __future__ import annotations

import json
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from jsonschema import Draft202012Validator, FormatChecker

from detent.contract import load_schema
from detent.identity import canonical_digest

__all__ = [
    "Adapter",
    "DispatchOrder",
    "DispatchResult",
    "StatusAnswer",
    "declarations_dir",
    "load_declaration",
]


@dataclass(frozen=True, slots=True)
class DispatchOrder:
    """What the dispatcher hands the adapter: identity-derived references plus
    the VALIDATED payload (the adapter never sees raw model output)."""

    operation_id: str
    effect_type: str
    payload: dict[str, Any]
    client_ref: str  # derived only from operation_id (master doc §7.2)


@dataclass(frozen=True, slots=True)
class DispatchResult:
    transport_outcome: str  # OK | FAILED | TIMEOUT | LOST (closed set, §10)
    failure_kind: str | None = None  # TERMINAL | RETRYABLE, iff FAILED
    destination_ref: str | None = None
    response_digest: str | None = None
    evidence: dict[str, Any] = field(default_factory=dict)


@dataclass(frozen=True, slots=True)
class StatusAnswer:
    """Authoritative read result in the status_probes vocabulary."""

    result: str  # PRESENT | ABSENT | INDETERMINATE
    n_found: int | None = None
    destination_refs: tuple[str, ...] = ()
    evidence: dict[str, Any] = field(default_factory=dict)


def declarations_dir() -> Path:
    """The packaged reference-destination capability declarations."""
    return Path(__file__).resolve().parent / "declarations"


def load_declaration(path: Path) -> dict[str, Any]:
    """Load and schema-validate a capability declaration; the core refuses to
    operate an adapter whose declaration fails validation (adapters.md §1.1)."""
    declaration = json.loads(path.read_text(encoding="utf-8"))
    schema = load_schema("capability-declaration.schema.json")
    validator = Draft202012Validator(schema, format_checker=FormatChecker())
    errors = list(validator.iter_errors(declaration))
    if errors:
        raise ValueError(
            f"capability declaration {path.name} fails schema validation: "
            + "; ".join(e.message for e in errors)
        )
    if not isinstance(declaration, dict):  # pragma: no cover
        raise TypeError("declaration must be a JSON object")
    return declaration


class Adapter(ABC):
    """One destination binding: credentials-handle + pinned declaration +
    transport client."""

    adapter_id: str

    @abstractmethod
    def declare(self) -> dict[str, Any]:
        """Static, side-effect-free, schema-valid capability declaration."""

    def declaration_digest(self) -> str:
        return canonical_digest(self.declare())

    @abstractmethod
    def dispatch(self, order: DispatchOrder, deadline_s: float) -> DispatchResult:
        """Exactly one wire attempt of the destination call."""

    @abstractmethod
    def status_query(
        self,
        *,
        client_ref: str | None = None,
        destination_ref: str | None = None,
        deadline_s: float = 10.0,
    ) -> StatusAnswer:
        """Authoritative read by the strongest available key. ABSENT requires
        an authoritative destination answer (e.g. 404 on a canonical retrieve),
        never a transport failure."""

    @abstractmethod
    def list_effects(
        self, window_from: str, window_to: str, deadline_s: float = 10.0
    ) -> list[dict[str, Any]]:
        """Orphan-sweep feed; only where the declaration says list_queryable."""
