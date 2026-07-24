"""EasyPost C2 adapter — DRAFT, credential-gated, pending ADR-0012 (C2 sandbox).

Status honesty: never made a live call; prepared mechanism for the P4 spike
(EasyPost is ADR-0012's recorded fallback candidate). Semantics from official
docs (research pass 2026-07-22; citations in the declaration):

- Shipment creation has NO request idempotency key (fits C2); the caller-set
  ``reference`` field is echoed on read-back and usable in place of the id on
  many endpoints — but it is NOT unique and NOT a list filter, so the
  declaration exposes ``queryable.by = [destination_ref]`` only and relies on
  windowed enumeration for reconciliation coverage (the §6.1 key-coverage
  rule then routes through k2/k3 honestly).
- Test-mode objects are retained 30 days — the declaration's enumeration
  horizon; list endpoints are rate-limited (~5 req/s) with cursor paging
  (``before_id``, ``page_size`` ≤ 100).
- Error taxonomy: 422 validation errors are documented, side-effect-free
  rejections → FAILED TERMINAL; 429 → FAILED RETRYABLE; everything
  unrecognized → LOST (RFC-002 §10).
"""

from __future__ import annotations

import base64
import os
from typing import Any

from irrevon.adapters.base import Adapter, DispatchOrder, DispatchResult, StatusAnswer
from irrevon.adapters.httpapi import Transport, urllib_transport
from irrevon.adapters.refdest import WireDropped
from irrevon.errors import CapabilityUnsupported, ConfigInvalid
from irrevon.identity import canonical_digest

__all__ = ["EasyPostC2Adapter"]

_BASE = "https://api.easypost.com"
_EFFECT_TYPE = "shipment.create"
_REQUIRED_SHIPMENT_FIELDS = ("to_address", "from_address", "parcel")


class EasyPostC2Adapter(Adapter):
    def __init__(
        self,
        adapter_id: str,
        declaration: dict[str, Any],
        api_key: str,
        *,
        transport: Transport = urllib_transport,
        base_url: str = _BASE,
    ) -> None:
        if not api_key or not api_key.startswith("EZTK"):
            # Test-key prefix required: production keys (EZAK) are refused.
            raise ConfigInvalid(
                "EasyPost adapter accepts TEST API keys only (EZTK prefix); refusing to construct"
            )
        self.adapter_id = adapter_id
        self._declaration = declaration
        self._api_key = api_key
        self._transport = transport
        self._base = base_url.rstrip("/")

    @classmethod
    def from_env(
        cls,
        adapter_id: str,
        declaration: dict[str, Any],
        *,
        key_env: str = "IRREVON_EASYPOST_TEST_KEY",
        transport: Transport = urllib_transport,
    ) -> EasyPostC2Adapter:
        api_key = os.environ.get(key_env, "")
        if not api_key:
            raise ConfigInvalid(
                f"EasyPost adapter requires the {key_env} environment variable "
                "(test API key); it is unset — this adapter is credential-gated "
                "and never runs without one"
            )
        return cls(adapter_id, declaration, api_key, transport=transport)

    def declare(self) -> dict[str, Any]:
        return self._declaration

    def _headers(self) -> dict[str, str]:
        token = base64.b64encode(f"{self._api_key}:".encode()).decode()
        return {"Authorization": f"Basic {token}"}

    # ── protocol operations ────────────────────────────────────────────────────

    def dispatch(self, order: DispatchOrder, deadline_s: float) -> DispatchResult:
        if order.effect_type != _EFFECT_TYPE:
            raise CapabilityUnsupported(
                f"adapter {self.adapter_id} supports {_EFFECT_TYPE!r}, not {order.effect_type!r}"
            )
        missing = [key for key in _REQUIRED_SHIPMENT_FIELDS if key not in order.payload]
        if missing:
            raise CapabilityUnsupported(
                "EasyPost shipment payload is missing required fields: "
                + ", ".join(missing)
            )
        if "reference" in order.payload:
            raise CapabilityUnsupported(
                "EasyPost reference is identity-reserved and derived from operation_id"
            )
        body = {"shipment": {**order.payload, "reference": order.client_ref}}
        evidence: dict[str, Any] = {
            "adapter_id": self.adapter_id,
            "client_ref": order.client_ref,
            "request_digest": canonical_digest(
                {
                    "effect_type": order.effect_type,
                    "payload_digest": canonical_digest(body),
                }
            ),
        }
        try:
            http_response = self._transport(
                "POST", f"{self._base}/v2/shipments", body, self._headers(), deadline_s
            )
        except WireDropped:
            return DispatchResult(
                "LOST", evidence={**evidence, "send_state": "sent_no_response"}
            )
        except TimeoutError:
            return DispatchResult(
                "TIMEOUT", evidence={**evidence, "deadline_s": deadline_s}
            )
        status, response = http_response.status, http_response.body
        response_headers = http_response.selected_headers(
            "Retry-After", "X-RateLimit-Limit", "X-RateLimit-Remaining", "X-Request-Id"
        )
        header_evidence = (
            {"response_headers": response_headers} if response_headers else {}
        )
        digest = canonical_digest(response)
        if (
            status in (200, 201)
            and isinstance(response.get("id"), str)
            and response["id"]
        ):
            return DispatchResult(
                "OK",
                destination_ref=response["id"],
                response_digest=digest,
                evidence={**evidence, "status": status, **header_evidence},
            )
        if status == 429:
            return DispatchResult(
                "FAILED",
                failure_kind="RETRYABLE",
                response_digest=digest,
                evidence={
                    **evidence,
                    "status": status,
                    "throttled": True,
                    **header_evidence,
                },
            )
        if status == 422:
            # Documented validation rejection: nothing was created.
            return DispatchResult(
                "FAILED",
                failure_kind="TERMINAL",
                response_digest=digest,
                evidence={
                    **evidence,
                    "status": status,
                    "error": "validation",
                    **header_evidence,
                },
            )
        return DispatchResult(
            "LOST",
            response_digest=digest,
            evidence={
                **evidence,
                "status": status,
                "unrecognized": True,
                **header_evidence,
            },
        )

    def status_query(
        self,
        *,
        client_ref: str | None = None,
        destination_ref: str | None = None,
        deadline_s: float = 10.0,
    ) -> StatusAnswer:
        if destination_ref is None:
            # The declaration says so: reference is NOT a supported query key
            # (not unique, not filterable) — reconciliation must use k2/k3.
            raise CapabilityUnsupported(
                f"adapter {self.adapter_id}: declaration exposes destination_ref "
                "queries only (EasyPost reference is not a query filter)"
            )
        try:
            response = self._transport(
                "GET",
                f"{self._base}/v2/shipments/{destination_ref}",
                None,
                self._headers(),
                deadline_s,
            )
        except (WireDropped, TimeoutError) as err:
            return StatusAnswer(
                "INDETERMINATE", None, (), {"transport_error": type(err).__name__}
            )
        status, body = response.status, response.body
        if status == 200 and isinstance(body.get("id"), str) and body["id"]:
            return StatusAnswer(
                "PRESENT",
                1,
                (body["id"],),
                {"status": status, "response_digest": canonical_digest(body)},
            )
        if status == 404:
            return StatusAnswer(
                "ABSENT", 0, (), {"status": status, "authoritative_absent": True}
            )
        return StatusAnswer("INDETERMINATE", None, (), {"status": status})

    def list_effects(
        self, window_from: str, window_to: str, deadline_s: float = 10.0
    ) -> list[dict[str, Any]]:
        out: list[dict[str, Any]] = []
        before_id: str | None = None
        for _ in range(100):  # pagination hard stop
            url = (
                f"{self._base}/v2/shipments?page_size=100&purchased=false"
                f"&start_datetime={window_from}&end_datetime={window_to}"
            )
            if before_id:
                url += f"&before_id={before_id}"
            response = self._transport("GET", url, None, self._headers(), deadline_s)
            status, body = response.status, response.body
            shipments = body.get("shipments")
            if (
                status != 200
                or not isinstance(shipments, list)
                or not all(isinstance(item, dict) for item in shipments)
            ):
                raise CapabilityUnsupported(f"list failed with status {status}")
            if any(
                not isinstance(item.get("id"), str) or not item["id"]
                for item in shipments
            ):
                raise CapabilityUnsupported("list returned an invalid shipment id")
            for item in shipments:
                out.append(
                    {
                        "destination_ref": item["id"],
                        "effect_type": "shipment",
                        "client_ref": item.get("reference"),
                        "created_at": item.get("created_at"),
                        "status": item.get("status"),
                    }
                )
            if not body.get("has_more") or not shipments:
                return out
            before_id = shipments[-1]["id"]
        raise CapabilityUnsupported("pagination exceeded the hard stop")
