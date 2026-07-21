"""Runtime taint canary for model-generated payloads (testing.md §4.1 leg B).

The registrar wraps the incoming ``parameters`` payload in :class:`ModelTainted`
immediately after schema validation. Every implicit conversion a derivation path
could take — str, bytes, iteration, indexing, formatting — raises
:class:`TaintViolation`, so model output physically cannot flow into identity or
idempotency derivation without exploding a test. The ONE sanctioned exit is
:meth:`ModelTainted.reveal_for_adapter`, called at the adapter boundary where the
destination request is built (RFC-002 §14: wire I/O lives only in adapters).
"""

from __future__ import annotations

from typing import Any, Never, NoReturn


class TaintViolation(RuntimeError):
    """Model-tainted content reached a code path that tried to consume it."""


class ModelTainted:
    """Opaque container for a model-generated payload."""

    __slots__ = ("_value",)

    def __init__(self, value: object) -> None:
        object.__setattr__(self, "_value", value)

    def reveal_for_adapter(self) -> object:
        """The one sanctioned unwrap, for adapter request construction only."""
        return object.__getattribute__(self, "_value")

    def _explode(self, via: str) -> NoReturn:
        raise TaintViolation(
            f"model-tainted payload consumed via {via}: model output must never "
            "reach identity, idempotency, or evidence derivation (master doc §7.2)"
        )

    def __str__(self) -> str:
        self._explode("__str__")

    def __repr__(self) -> str:
        return "ModelTainted(<opaque>)"

    def __bytes__(self) -> bytes:
        self._explode("__bytes__")

    def __iter__(self) -> Never:
        self._explode("__iter__")

    def __len__(self) -> int:
        self._explode("__len__")

    def __getitem__(self, key: object) -> Never:
        self._explode("__getitem__")

    def __contains__(self, item: object) -> bool:
        self._explode("__contains__")

    def __format__(self, format_spec: str) -> str:
        self._explode("__format__")

    def __eq__(self, other: object) -> bool:
        self._explode("__eq__")

    def __hash__(self) -> int:
        self._explode("__hash__")

    def __bool__(self) -> bool:
        self._explode("__bool__")

    # json.JSONEncoder falls back to __dict__-free objects via default(); there is
    # no hook to intercept, but keys() absence already breaks dict(); this guards
    # libraries that duck-type mappings.
    def keys(self) -> Never:
        self._explode("keys")

    def items(self) -> Never:
        self._explode("items")

    def values(self) -> Never:
        self._explode("values")

    def get(self, key: object, default: object = None) -> Any:
        self._explode("get")
