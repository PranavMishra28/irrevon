"""Intent-contract validation — the trust boundary (master doc §6.3).

Validates raw registration input against ``schemas/intent-contract.schema.json``
(the ONLY channel by which model-generated content reaches the deterministic
core), computes the canonical parameters digest as evidence, and wraps the
model-shaped ``parameters`` payload in the taint canary before anything
downstream can touch it.
"""

from __future__ import annotations

import json
import math
from dataclasses import dataclass, field
from functools import cache
from pathlib import Path
from typing import Any

from jsonschema import Draft202012Validator, FormatChecker

from irrevon.contract.taint import ModelTainted
from irrevon.errors import ContractInvalid
from irrevon.identity import canonical_digest

__all__ = ["IntentContract", "load_schema", "validate_intent_contract"]

_SCHEMA_FILENAME = "intent-contract.schema.json"
_MAX_DEPTH = 32
_MAX_NODES = 10_000
_MAX_SCALAR_BYTES = 1024 * 1024
_MAX_STRING_BYTES = 64 * 1024
_MAX_SAFE_INTEGER = 2**53 - 1


def _preflight_json(value: object) -> None:
    """Bound untrusted JSON without recursion before schema/JCS processing."""
    stack: list[tuple[object, int]] = [(value, 0)]
    nodes = 0
    scalar_bytes = 0
    while stack:
        current, depth = stack.pop()
        nodes += 1
        if nodes > _MAX_NODES:
            raise ContractInvalid("intent contract exceeds the 10000-node limit")
        if depth > _MAX_DEPTH:
            raise ContractInvalid("intent contract exceeds the depth-32 limit")
        if isinstance(current, dict):
            for key, child in current.items():
                if not isinstance(key, str):
                    raise ContractInvalid("intent contract object keys must be strings")
                try:
                    key_size = len(key.encode("utf-8"))
                except UnicodeEncodeError as err:
                    raise ContractInvalid(
                        "intent contract strings must be valid Unicode scalar values"
                    ) from err
                if key_size > _MAX_STRING_BYTES:
                    raise ContractInvalid("intent contract contains an oversized key")
                scalar_bytes += key_size
                stack.append((child, depth + 1))
        elif isinstance(current, list):
            stack.extend((child, depth + 1) for child in current)
        elif isinstance(current, str):
            try:
                size = len(current.encode("utf-8"))
            except UnicodeEncodeError as err:
                raise ContractInvalid(
                    "intent contract strings must be valid Unicode scalar values"
                ) from err
            if size > _MAX_STRING_BYTES:
                raise ContractInvalid("intent contract contains an oversized string")
            scalar_bytes += size
        elif isinstance(current, bool) or current is None:
            scalar_bytes += 5
        elif isinstance(current, int):
            if not -_MAX_SAFE_INTEGER <= current <= _MAX_SAFE_INTEGER:
                raise ContractInvalid(
                    "intent contract integer is outside the I-JSON range"
                )
            scalar_bytes += len(str(current))
        elif isinstance(current, float):
            if not math.isfinite(current):
                raise ContractInvalid("intent contract numbers must be finite")
            scalar_bytes += 24
        else:
            raise ContractInvalid(
                f"intent contract contains unsupported JSON type {type(current).__name__}"
            )
        if scalar_bytes > _MAX_SCALAR_BYTES:
            raise ContractInvalid("intent contract exceeds the 1 MiB scalar-data limit")


def _find_schemas_dir() -> Path:
    """Locate the canonical ``schemas/`` directory.

    Editable/dev installs resolve the repo root by walking up from this file;
    built wheels carry a copy under ``irrevon/_schemas`` (hatchling force-include).
    """
    packaged = Path(__file__).resolve().parent.parent / "_schemas"
    if (packaged / _SCHEMA_FILENAME).is_file():
        return packaged
    for parent in Path(__file__).resolve().parents:
        candidate = parent / "schemas"
        if (candidate / _SCHEMA_FILENAME).is_file():
            return candidate
    raise FileNotFoundError(
        "schemas/ directory not found (repo checkout or packaged copy required)"
    )


@cache
def load_schema(name: str) -> dict[str, Any]:
    """Load a schema resource by file name from the canonical schemas directory."""
    path = _find_schemas_dir() / name
    loaded = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(loaded, dict):  # pragma: no cover - schema files are objects
        raise TypeError(f"schema {name} is not a JSON object")
    return loaded


@cache
def _intent_validator() -> Draft202012Validator:
    schema = load_schema(_SCHEMA_FILENAME)
    Draft202012Validator.check_schema(schema)
    return Draft202012Validator(schema, format_checker=FormatChecker())


@dataclass(frozen=True, slots=True)
class IntentContract:
    """A validated intent contract (ADR-0019 shape).

    ``parameters`` is taint-wrapped: it is a carrier, never an identity input,
    and only the adapter boundary may reveal it. ``parameters_digest`` is the
    canonical evidence digest computed at validation time.
    ``canonical_source`` preserves the raw (validated) object so the ledger can
    store the exact JCS bytes hashed into ``effect_id`` (RFC-002 §2.2).
    """

    schema_version: str
    stable_ids: dict[str, str]
    effect_type: str
    effect_class: str
    scope: str
    adapter_id: str
    parameters: ModelTainted = field(compare=False)
    parameters_digest: str
    authority_ref: str
    stamped_at: str
    branch_ref: str | None = None
    event_time: str | None = None


def validate_intent_contract(raw: object) -> IntentContract:
    """Validate raw registration input and produce a taint-wrapped contract.

    Raises :class:`ContractInvalid` (stable code ``contract_invalid``) with the
    schema errors in ``details`` — including the no-stable-id rejection (master
    doc §6.1).
    """
    if not isinstance(raw, dict):
        raise ContractInvalid(
            "intent contract must be a JSON object",
            details={"errors": [f"expected object, got {type(raw).__name__}"]},
        )
    try:
        _preflight_json(raw)
    except ContractInvalid as err:
        if err.details.get("errors"):
            raise
        raise ContractInvalid(
            err.message,
            details={"errors": [{"path": "", "message": err.message}]},
        ) from err
    errors = sorted(
        _intent_validator().iter_errors(raw), key=lambda e: list(e.absolute_path)
    )
    if errors:
        raise ContractInvalid(
            "intent contract failed schema validation",
            details={
                "errors": [
                    {
                        "path": "/".join(str(p) for p in e.absolute_path),
                        "message": e.message,
                    }
                    for e in errors
                ]
            },
        )
    parameters: dict[str, Any] = raw["parameters"]
    try:
        parameters_digest = canonical_digest(parameters)
    except (ValueError, TypeError, OverflowError, RecursionError) as err:
        raise ContractInvalid(
            "intent contract cannot be represented in the canonical JSON domain"
        ) from err
    return IntentContract(
        schema_version=raw["schema_version"],
        stable_ids=dict(raw["stable_ids"]),
        effect_type=raw["effect_type"],
        effect_class=raw["effect_class"],
        scope=raw["scope"],
        adapter_id=raw["adapter_id"],
        parameters=ModelTainted(parameters),
        parameters_digest=parameters_digest,
        authority_ref=raw["authority_ref"],
        stamped_at=raw["stamped_at"],
        branch_ref=raw.get("branch_ref"),
        event_time=raw.get("event_time"),
    )
