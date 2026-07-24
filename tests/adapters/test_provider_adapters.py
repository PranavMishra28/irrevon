"""Provider adapters (Stripe C1 / EasyPost C2) — SYNTHETIC transport only.

Every response below is fabricated test data exercising the adapter's
declaration-cited classification and query logic. Nothing here is provider
evidence; live behavior is verified only at the human-gated ADR-0010/0012
spikes with credentials and ToS approval."""

from __future__ import annotations

from typing import Any

import pytest

from irrevon.adapters.base import DispatchOrder, declarations_dir, load_declaration
from irrevon.adapters.easypost_c2 import EasyPostC2Adapter
from irrevon.adapters.httpapi import HttpResponse
from irrevon.adapters.refdest import WireDropped
from irrevon.adapters.stripe_c1 import StripeC1Adapter
from irrevon.errors import CapabilityUnsupported, ConfigInvalid

STRIPE_DECL = load_declaration(declarations_dir() / "stripe-c1.capability.json")
EASYPOST_DECL = load_declaration(declarations_dir() / "easypost-c2.capability.json")

ORDER = DispatchOrder(
    operation_id="a" * 64 + ":0",
    effect_type="payment_intent.create",
    payload={"amount": 1250, "currency": "usd"},
    client_ref="a" * 64 + ":0",
)


class _FakeTransport:
    """Synthetic wire: scripted (status, body) responses + request capture."""

    def __init__(self, responses: list[Any]) -> None:
        self.responses = list(responses)
        self.requests: list[dict[str, Any]] = []

    def __call__(
        self, method: str, url: str, body: Any, headers: dict[str, str], deadline: float
    ) -> HttpResponse:
        self.requests.append(
            {"method": method, "url": url, "body": body, "headers": dict(headers)}
        )
        response = self.responses.pop(0)
        if isinstance(response, Exception):
            raise response
        if isinstance(response, HttpResponse):
            return response
        status, body = response
        return HttpResponse(status, body)


def _stripe(responses: list[Any]) -> tuple[StripeC1Adapter, _FakeTransport]:
    transport = _FakeTransport(responses)
    return (
        StripeC1Adapter("stripe-c1", STRIPE_DECL, "sk_test_synthetic", transport=transport),
        transport,
    )


def _easypost(responses: list[Any]) -> tuple[EasyPostC2Adapter, _FakeTransport]:
    transport = _FakeTransport(responses)
    return (
        EasyPostC2Adapter("easypost-c2", EASYPOST_DECL, "EZTK_synthetic", transport=transport),
        transport,
    )


# ── credential gating ──────────────────────────────────────────────────────────


def test_stripe_refuses_without_env(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv("IRREVON_STRIPE_SANDBOX_KEY", raising=False)
    with pytest.raises(ConfigInvalid, match="credential-gated"):
        StripeC1Adapter.from_env("stripe-c1", STRIPE_DECL)


def test_stripe_refuses_live_mode_keys() -> None:
    with pytest.raises(ConfigInvalid, match="SANDBOX secret keys only"):
        StripeC1Adapter("stripe-c1", STRIPE_DECL, "sk_live_forbidden")


def test_easypost_refuses_production_keys() -> None:
    with pytest.raises(ConfigInvalid, match="TEST API keys only"):
        EasyPostC2Adapter("easypost-c2", EASYPOST_DECL, "EZAK_production")


# ── Stripe wire discipline + classification ────────────────────────────────────


def test_stripe_sends_idempotency_key_version_and_metadata() -> None:
    adapter, transport = _stripe([(200, {"id": "pi_1", "status": "succeeded"})])
    result = adapter.dispatch(ORDER, 10.0)
    assert result.transport_outcome == "OK"
    assert result.destination_ref == "pi_1"
    request = transport.requests[0]
    assert request["headers"]["Idempotency-Key"] == ORDER.client_ref
    assert request["headers"]["Stripe-Version"] == STRIPE_DECL["api_version"]
    assert request["body"]["metadata[irrevon_ref]"] == ORDER.client_ref
    # The secret key never leaks into evidence.
    assert "sk_test" not in str(result.evidence)


@pytest.mark.parametrize(
    ("status", "body", "outcome", "kind"),
    [
        (402, {"error": {"type": "card_error"}}, "FAILED", "TERMINAL"),
        (400, {"error": {"type": "invalid_request_error"}}, "FAILED", "TERMINAL"),
        (409, {"error": {"type": "idempotency_error"}}, "FAILED", "TERMINAL"),
        (500, {"error": {"type": "api_error"}}, "LOST", None),
        (200, {"weird": True}, "LOST", None),  # unrecognized success shape
    ],
)
def test_stripe_classification_table(
    status: int, body: dict[str, Any], outcome: str, kind: str | None
) -> None:
    adapter, _ = _stripe([(status, body)])
    result = adapter.dispatch(ORDER, 10.0)
    assert result.transport_outcome == outcome
    assert result.failure_kind == kind


def test_stripe_wire_drop_and_timeout_are_ambiguous() -> None:
    adapter, _ = _stripe([WireDropped(committed=False)])
    assert adapter.dispatch(ORDER, 10.0).transport_outcome == "LOST"
    adapter, _ = _stripe([TimeoutError()])
    assert adapter.dispatch(ORDER, 10.0).transport_outcome == "TIMEOUT"


def test_stripe_429_requires_documented_rate_limit_header() -> None:
    adapter, _ = _stripe(
        [
            HttpResponse(
                429,
                {"error": {"type": "rate_limit_error"}},
                {
                    "Stripe-Rate-Limited-Reason": "global-rate",
                    "Retry-After": "2",
                    "Set-Cookie": "must-not-enter-evidence",
                },
            )
        ]
    )
    result = adapter.dispatch(ORDER, 10.0)
    assert (result.transport_outcome, result.failure_kind) == ("FAILED", "RETRYABLE")
    assert result.evidence["response_headers"] == {
        "retry-after": "2",
        "stripe-rate-limited-reason": "global-rate",
    }

    adapter, _ = _stripe([(429, {"error": {"type": "rate_limit_error"}})])
    assert adapter.dispatch(ORDER, 10.0).transport_outcome == "LOST"


@pytest.mark.parametrize(
    "order",
    [
        DispatchOrder("x", "shipment.create", {"amount": 100, "currency": "usd"}, "x"),
        DispatchOrder(
            "x",
            "payment_intent.create",
            {"amount": 100, "currency": "usd", "extra": {"confirm": True}},
            "x",
        ),
        DispatchOrder(
            "x",
            "payment_intent.create",
            {
                "amount": 100,
                "currency": "usd",
                "extra": {"metadata[irrevon_ref]": "attacker-controlled"},
            },
            "x",
        ),
    ],
)
def test_stripe_rejects_wrong_effect_or_reserved_parameters(
    order: DispatchOrder,
) -> None:
    adapter, transport = _stripe([])
    with pytest.raises(CapabilityUnsupported):
        adapter.dispatch(order, 10.0)
    assert transport.requests == []


def test_stripe_status_query_mapping() -> None:
    adapter, _ = _stripe([(200, {"id": "pi_1"})])
    assert adapter.status_query(destination_ref="pi_1").result == "PRESENT"
    adapter, _ = _stripe([(404, {"error": {"code": "resource_missing"}})])
    assert adapter.status_query(destination_ref="pi_x").result == "ABSENT"
    adapter, _ = _stripe([(500, {})])
    assert adapter.status_query(destination_ref="pi_1").result == "INDETERMINATE"
    adapter, _ = _stripe([(200, {"data": [{"id": "pi_1"}, {"id": "pi_2"}]})])
    answer = adapter.status_query(client_ref=ORDER.client_ref)
    assert (answer.result, answer.n_found) == ("PRESENT", 2)
    adapter, _ = _stripe([(200, {"data": []})])
    assert adapter.status_query(client_ref=ORDER.client_ref).result == "ABSENT"


def test_stripe_list_paginates_with_cursor() -> None:
    adapter, transport = _stripe(
        [
            (200, {"data": [{"id": "pi_1", "metadata": {"irrevon_ref": "r1"}}],
                   "has_more": True}),
            (200, {"data": [{"id": "pi_2", "metadata": {}}], "has_more": False}),
        ]
    )
    listed = adapter.list_effects("2026-07-01T00:00:00Z", "2026-07-22T00:00:00Z")
    assert [e["destination_ref"] for e in listed] == ["pi_1", "pi_2"]
    assert "starting_after=pi_1" in transport.requests[1]["url"]


# ── EasyPost wire discipline + declared query boundary ─────────────────────────


def test_easypost_stamps_reference_and_classifies() -> None:
    adapter, transport = _easypost([(201, {"id": "shp_1", "status": "created"})])
    order = DispatchOrder(
        operation_id="b" * 64 + ":0", effect_type="shipment.create",
        payload={
            "to_address": {"name": "Synthetic"},
            "from_address": {"name": "Synthetic sender"},
            "parcel": {"weight": 1},
        },
        client_ref="b" * 64 + ":0",
    )
    result = adapter.dispatch(order, 10.0)
    assert result.transport_outcome == "OK"
    assert transport.requests[0]["body"]["shipment"]["reference"] == order.client_ref
    assert transport.requests[0]["headers"]["Authorization"].startswith("Basic ")


@pytest.mark.parametrize(
    ("status", "outcome", "kind"),
    [(422, "FAILED", "TERMINAL"), (429, "FAILED", "RETRYABLE"), (503, "LOST", None)],
)
def test_easypost_classification(status: int, outcome: str, kind: str | None) -> None:
    adapter, _ = _easypost([(status, {"error": {"message": "synthetic"}})])
    order = DispatchOrder(
        operation_id="b" * 64 + ":0", effect_type="shipment.create",
        payload={"to_address": "adr_to", "from_address": "adr_from", "parcel": "prcl_1"},
        client_ref="b" * 64 + ":0",
    )
    result = adapter.dispatch(order, 10.0)
    assert (result.transport_outcome, result.failure_kind) == (outcome, kind)


def test_easypost_declares_no_client_ref_query() -> None:
    """The declared boundary, enforced: reference is not a query filter, so a
    client_ref status query is a capability error — reconciliation must route
    through destination_ref or enumeration (RFC-002 §6.1 key coverage)."""
    adapter, _ = _easypost([])
    with pytest.raises(CapabilityUnsupported, match="destination_ref"):
        adapter.status_query(client_ref="ref-1")


def test_easypost_list_paginates_with_before_id() -> None:
    adapter, transport = _easypost(
        [
            (200, {"shipments": [{"id": "shp_2", "reference": "r2"}], "has_more": True}),
            (200, {"shipments": [{"id": "shp_1", "reference": "r1"}], "has_more": False}),
        ]
    )
    listed = adapter.list_effects("2026-07-01T00:00:00Z", "2026-07-22T00:00:00Z")
    assert [e["destination_ref"] for e in listed] == ["shp_2", "shp_1"]
    assert "purchased=false" in transport.requests[0]["url"]
    assert "before_id=shp_2" in transport.requests[1]["url"]


def test_easypost_rejects_wrong_effect_missing_fields_and_reference_override() -> None:
    invalid_orders = [
        DispatchOrder("x", "payment_intent.create", {}, "x"),
        DispatchOrder("x", "shipment.create", {}, "x"),
        DispatchOrder(
            "x",
            "shipment.create",
            {
                "to_address": "adr_to",
                "from_address": "adr_from",
                "parcel": "prcl_1",
                "reference": "caller-controlled",
            },
            "x",
        ),
    ]
    for order in invalid_orders:
        adapter, transport = _easypost([])
        with pytest.raises(CapabilityUnsupported):
            adapter.dispatch(order, 10.0)
        assert transport.requests == []


def test_easypost_pagination_refuses_missing_cursor() -> None:
    adapter, _ = _easypost([(200, {"shipments": [{}], "has_more": True})])
    with pytest.raises(CapabilityUnsupported, match="terminal shipment id"):
        adapter.list_effects("2026-07-01T00:00:00Z", "2026-07-22T00:00:00Z")


def test_declarations_schema_validate_and_declare_draft_status() -> None:
    for declaration in (STRIPE_DECL, EASYPOST_DECL):
        assert declaration["evidence_quality"] == "EI"
        assert "DRAFT" in declaration["destination"]
        assert "no live call" in declaration["attribution"]["notes"]
