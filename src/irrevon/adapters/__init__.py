"""Adapters — the ONLY module where wire I/O lives (RFC-002 §14).

Includes the adapter protocol (ADR-005; adapters.md §1) and the deterministic
reference destinations (RFC-002 §8).
"""

from irrevon.adapters.base import (
    Adapter,
    DispatchOrder,
    DispatchResult,
    StatusAnswer,
    load_declaration,
)
from irrevon.adapters.refdest import RefDest, RefdestAdapter, WireDropped

__all__ = [
    "Adapter",
    "DispatchOrder",
    "DispatchResult",
    "RefDest",
    "RefdestAdapter",
    "StatusAnswer",
    "WireDropped",
    "load_declaration",
]
