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

from detent import SCHEMA_VERSION


class DetentError(Exception):
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


class ContractInvalid(DetentError):
    """Intent contract failed schema validation (incl. the no-stable-id rejection)."""

    code = "contract_invalid"


class NotFound(DetentError):
    code = "not_found"


class IllegalState(DetentError):
    """Operation not legal from the record's current lifecycle (RFC-002 §3.1)."""

    code = "illegal_state"


class IdentityConflict(DetentError):
    """Same identity tuple re-registered with different must-match members (RFC-002 §1)."""

    code = "identity_conflict"


class CapabilityUnsupported(DetentError):
    """Adapter's capability declaration lacks the needed hook (e.g. sweep w/o list_queryable)."""

    code = "capability_unsupported"


class AdapterUnavailable(DetentError):
    """Destination unreachable at transport level before any dispatch attempt was issued."""

    code = "adapter_unavailable"
    retryable = True


class ScopeBusy(DetentError):
    """Per-(scope, effect_type) serialization: an open attempt exists in the slot (§5.1)."""

    code = "scope_busy"
    retryable = True


class ResolutionInvalid(DetentError):
    """resolve() action/evidence violates the dimension-C legality table (RFC-002 §3.3)."""

    code = "resolution_invalid"


class StorageUnavailable(DetentError):
    """Ledger unreachable; nothing was dispatched (persist-before-dispatch ordering)."""

    code = "storage_unavailable"
    retryable = True


class ConfigInvalid(DetentError):
    code = "config_invalid"
