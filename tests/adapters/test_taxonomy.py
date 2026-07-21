"""Transport-taxonomy property (testing.md §4.8 part 1; RFC-002 §10).

Conformance: master doc §12.1 row 8 — "Ambiguous outcomes surfaced, never
silently resolved" (taxonomy leg): a wide Hypothesis corpus of unrecognized
destination responses — unknown status codes, malformed bodies, success-shaped
bodies with failure codes and vice versa — must map to LOST/TIMEOUT (→
AMBIGUOUS), NEVER FAILED. Only the declaration-cited shapes (the documented
pre-execution 429; the documented invalid_request 400) may map to FAILED.
"""

from __future__ import annotations

from typing import Any

from hypothesis import given
from hypothesis import strategies as st

from detent.adapters.base import declarations_dir, load_declaration
from detent.adapters.refdest import RefDest, RefdestAdapter

C2_DECL = load_declaration(declarations_dir() / "refdest-c2.capability.json")


def _adapter() -> RefdestAdapter:
    return RefdestAdapter("refdest-c2", C2_DECL, instance=RefDest())


_RECOGNIZED_OK = {200, 201, 202}

_body = st.one_of(
    st.dictionaries(st.text(max_size=12), st.text(max_size=24), max_size=4),
    st.fixed_dictionaries({"error": st.text(max_size=24)}),
    # Success-shaped body with a failure code and vice versa:
    st.fixed_dictionaries({"destination_ref": st.text(min_size=1, max_size=12)}),
    st.fixed_dictionaries({"error": st.just("invalid_request")}),
    st.just({}),
)


@given(status=st.integers(min_value=100, max_value=599), body=_body)
def test_unknown_is_ambiguous_never_failed(status: int, body: dict[str, Any]) -> None:
    result = _adapter()._classify(status, body, {})
    if status in _RECOGNIZED_OK:
        assert result.transport_outcome == "OK"
    elif status == 429:
        # Declaration-cited pre-execution throttle: provably side-effect-free.
        assert result.transport_outcome == "FAILED"
        assert result.failure_kind == "RETRYABLE"
    elif status == 400 and body.get("error") == "invalid_request":
        assert result.transport_outcome == "FAILED"
        assert result.failure_kind == "TERMINAL"
    else:
        # EVERYTHING else: evidence is never discarded by optimistic
        # classification — LOST, never FAILED (RFC-002 §10).
        assert result.transport_outcome == "LOST", (
            f"status {status} with body {body} classified "
            f"{result.transport_outcome}; unknown must be AMBIGUOUS, never FAILED"
        )
        assert result.failure_kind is None


@given(status=st.integers(min_value=100, max_value=599), body=_body)
def test_failed_always_carries_declared_citation_shape(
    status: int, body: dict[str, Any]
) -> None:
    """An adapter classifying an undeclared error shape as FAILED fails its
    negative contract test (RFC-002 §10)."""
    result = _adapter()._classify(status, body, {})
    if result.transport_outcome == "FAILED":
        assert status in (429, 400), "only declaration-cited shapes may FAIL"


def test_wire_drop_maps_to_lost() -> None:
    from detent.adapters.base import DispatchOrder

    refdest = RefDest()
    adapter = RefdestAdapter("refdest-c2", C2_DECL, instance=refdest)
    refdest.control_schedule(
        [{"match": {"op": "create"}, "fault": "DROP_RESPONSE_BEFORE_COMMIT"}]
    )
    result = adapter.dispatch(
        DispatchOrder("a" * 64 + ":0", "order.create", {}, "a" * 64 + ":0"), 5.0
    )
    assert result.transport_outcome == "LOST"
    assert result.evidence["send_state"] == "sent_no_response"


def test_delay_past_deadline_maps_to_timeout() -> None:
    from detent.adapters.base import DispatchOrder

    refdest = RefDest()
    adapter = RefdestAdapter("refdest-c2", C2_DECL, instance=refdest)
    refdest.control_schedule(
        [{"match": {"op": "create"}, "fault": "DELAY",
          "param": {"ms": 60_000, "commit": True}}]
    )
    result = adapter.dispatch(
        DispatchOrder("b" * 64 + ":0", "order.create", {}, "b" * 64 + ":0"), 5.0
    )
    assert result.transport_outcome == "TIMEOUT"
    assert len(refdest.control_state()) == 1, "the effect committed server-side"


def test_failed_query_is_indeterminate_never_absent() -> None:
    refdest = RefDest()
    adapter = RefdestAdapter("refdest-c2", C2_DECL, instance=refdest)
    refdest.control_schedule([{"match": {"op": "query"}, "fault": "THROTTLE_429"}])
    answer = adapter.status_query(client_ref="c" * 64 + ":0", deadline_s=5.0)
    assert answer.result == "INDETERMINATE"


def test_c2_honesty_same_request_twice_two_effects() -> None:
    """The load-bearing C2 negative observation: the destination really does
    not dedup — identical request twice ⇒ two effects (adapters.md §1.6)."""
    from detent.adapters.base import DispatchOrder

    refdest = RefDest()
    adapter = RefdestAdapter("refdest-c2", C2_DECL, instance=refdest)
    order = DispatchOrder("d" * 64 + ":0", "order.create", {"same": True}, "d" * 64 + ":0")
    first = adapter.dispatch(order, 5.0)
    second = adapter.dispatch(order, 5.0)
    assert first.transport_outcome == second.transport_outcome == "OK"
    assert first.destination_ref != second.destination_ref
    assert len(refdest.control_state()) == 2, (
        "if this ever returns 1 the destination has gone C1 — declaration "
        "update + retest + deviation ADR (AM-11 watch)"
    )


def test_c1_profile_honors_key_within_window() -> None:
    from detent.adapters.base import DispatchOrder

    declaration = load_declaration(declarations_dir() / "refdest-c1.capability.json")
    refdest = RefDest(profile="C1")
    adapter = RefdestAdapter("refdest-c1", declaration, instance=refdest)
    order = DispatchOrder("e" * 64 + ":0", "order.create", {"x": 1}, "e" * 64 + ":0")
    first = adapter.dispatch(order, 5.0)
    replay = adapter.dispatch(order, 5.0)
    assert len(refdest.control_state()) == 1, "same key replays, no second effect"
    assert replay.evidence["replayed"] is True
    assert first.destination_ref == replay.destination_ref


def test_determinism_same_seed_same_refs() -> None:
    """Same seed + same canonicalized request sequence → byte-identical
    ground truth (RFC-002 §8)."""
    from detent.adapters.base import DispatchOrder

    states = []
    for _ in range(2):
        refdest = RefDest(seed=99)
        adapter = RefdestAdapter("refdest-c2", C2_DECL, instance=refdest)
        for i in range(3):
            adapter.dispatch(
                DispatchOrder(f"{'f' * 64}:{i}", "order.create", {"i": i}, f"{'f' * 64}:{i}"),
                5.0,
            )
        states.append(refdest.control_state())
    assert states[0] == states[1]
