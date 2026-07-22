"""Stable error envelope for the SDK surface.

Shape and the closed code set follow the developer-surface specification
(.scratch/rc/dx-api.md §1.3): every error carries a stable machine ``code``, a human
``message``, a ``retryable`` flag, and typed ``details``. Additions to the code set are
versioning events, not casual edits.

Deliberately NOT errors: gate denial (an evidenced outcome), AMBIGUOUS (a lifecycle
state carrying evidence), and reconcile finding nothing (an empty list).
"""

from __future__ import annotations

from typing import Any

from irrevon import SCHEMA_VERSION

ADVISORY_MARKER = "__irrevon_advisory__"
"""Marker key carried by serialized advisory/classifier output. Mutation APIs
reject any payload carrying it (ADR-006 type-level layer; RFC-002 §14). Lives
here so authority modules can enforce the rejection without importing
irrevon.advisory (which the import contract forbids)."""


class AdvisoryRejected(TypeError):
    """Classifier output reached a mutation API — architecturally forbidden."""


def reject_advisory(value: object, where: str) -> None:
    """Typed rejection of advisory output at every mutation boundary."""
    if isinstance(value, dict) and ADVISORY_MARKER in value:
        raise AdvisoryRejected(
            f"advisory/classifier output cannot reach {where}: the model is "
            "never on the authority path (master doc §6.3, ADR-006)"
        )
    if getattr(type(value), "__name__", "") == "ClassifierProposal" or hasattr(
        value, "proposed_action"
    ):
        raise AdvisoryRejected(
            f"a ClassifierProposal cannot reach {where}: proposals are advisory "
            "only (master doc §6.3, ADR-006)"
        )


class IrrevonError(Exception):
    """Base of the typed error hierarchy; one subclass per stable code."""

    code: str = "unexpected"
    retryable: bool = False

    def __init__(self, message: str, details: dict[str, Any] | None = None) -> None:
        super().__init__(message)
        self.message = message
        self.details: dict[str, Any] = details or {}

    def to_envelope(self) -> dict[str, Any]:
        """The language-neutral error envelope (dx-api §1.3)."""
        return {
            "schema_version": SCHEMA_VERSION,
            "error": {
                "code": self.code,
                "message": self.message,
                "retryable": self.retryable,
                "details": self.details,
            },
        }


class ContractInvalid(IrrevonError):
    """Intent contract failed schema validation (incl. the no-stable-id rejection)."""

    code = "contract_invalid"


class NotFound(IrrevonError):
    code = "not_found"


class IllegalState(IrrevonError):
    """Operation not legal from the record's current lifecycle (RFC-002 §3.1)."""

    code = "illegal_state"


class IdentityConflict(IrrevonError):
    """Same identity tuple re-registered with different must-match members (RFC-002 §1)."""

    code = "identity_conflict"


class CapabilityUnsupported(IrrevonError):
    """Adapter's capability declaration lacks the needed hook (e.g. sweep w/o list_queryable)."""

    code = "capability_unsupported"


class AdapterUnavailable(IrrevonError):
    """Destination unreachable at transport level before any dispatch attempt was issued."""

    code = "adapter_unavailable"
    retryable = True


class ScopeBusy(IrrevonError):
    """Per-(scope, effect_type) serialization: an open attempt exists in the slot (§5.1)."""

    code = "scope_busy"
    retryable = True


class ResolutionInvalid(IrrevonError):
    """resolve() action/evidence violates the dimension-C legality table (RFC-002 §3.3)."""

    code = "resolution_invalid"


class StorageUnavailable(IrrevonError):
    """Ledger unreachable; nothing was dispatched (persist-before-dispatch ordering)."""

    code = "storage_unavailable"
    retryable = True


class ConfigInvalid(IrrevonError):
    code = "config_invalid"
