"""Stripe C1 adapter — DRAFT, credential-gated, pending ADR-0010 (version pin).

Status honesty: this adapter has NEVER made a live call. It is the prepared
mechanism for the M4/P5 spike: version-pinned semantics from official docs
(research pass 2026-07-22, citations in the declaration), a synthetic-
transport test suite, and hard credential gating. Live use additionally
requires the human ADR-0010 ratification, sandbox credentials, and the
traffic-budget note in the review queue. Nothing here is provider evidence.

Semantics implemented (v1 payments namespace, per AM-5):

- ``Idempotency-Key`` = the engine-derived client reference (only from
  ``operation_id``), sent on every create; Stripe caches the first outcome
  (including errors) for ≥24 h and replays it; same key + different params
  ⇒ 409 ``idempotency_error`` (no new side effect).
- ``metadata[irrevon_ref]`` carries the same reference for read-back:
  Retrieve/List are strongly consistent; Search (the only metadata query)
  is explicitly NOT read-after-write safe — the declaration carries the
  documented worst-case search freshness as the settlement lag, so
  confirmed-absence follows RFC-002 §6.2 with an honest bound.
- Error taxonomy (RFC-002 §10): only declaration-cited, provably
  side-effect-free shapes map to FAILED; everything unrecognized is LOST.
"""

from __future__ import annotations

import os
from typing import Any

from irrevon.adapters.base import Adapter, DispatchOrder, DispatchResult, StatusAnswer
from irrevon.adapters.httpapi import HttpResponse, Transport, urllib_transport
from irrevon.adapters.refdest import WireDropped
from irrevon.errors import CapabilityUnsupported, ConfigInvalid
from irrevon.identity import canonical_digest

__all__ = ["StripeC1Adapter"]

_BASE = "https://api.stripe.com"
# Provider-documented, side-effect-free error types (citations in the
# declaration). Anything else — incl. api_error 5xx — is AMBIGUOUS territory.
_TERMINAL_ERROR_TYPES = {"invalid_request_error", "card_error", "idempotency_error"}
_EFFECT_TYPE = "payment_intent.create"
_RESERVED_EXTRA_KEYS = {
    "amount",
    "capture_method",
    "confirmation_method",
    "confirmation_token",
    "confirm",
    "currency",
    "mandate",
    "mandate_data",
    "off_session",
    "payment_method",
    "payment_method_data",
}


class StripeC1Adapter(Adapter):
    def __init__(
        self,
        adapter_id: str,
        declaration: dict[str, Any],
        api_key: str,
        *,
        transport: Transport = urllib_transport,
        base_url: str = _BASE,
    ) -> None:
        if not api_key or not api_key.startswith(("sk_test_", "rk_test_")):
            # Sandbox-only by construction: a live-mode secret key is refused
            # outright (master doc §9 — production credentials are an incident).
            raise ConfigInvalid(
                "Stripe adapter accepts SANDBOX secret keys only "
                "(sk_test_/rk_test_ prefix); refusing to construct"
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
        key_env: str = "IRREVON_STRIPE_SANDBOX_KEY",
        transport: Transport = urllib_transport,
    ) -> StripeC1Adapter:
        """Credential-gated construction: the KEY NAME comes from config; the
        value only ever from the environment."""
        api_key = os.environ.get(key_env, "")
        if not api_key:
            raise ConfigInvalid(
                f"Stripe adapter requires the {key_env} environment variable "
                "(sandbox secret key); it is unset — this adapter is "
                "credential-gated and never runs without one"
            )
        return cls(adapter_id, declaration, api_key, transport=transport)

    def declare(self) -> dict[str, Any]:
        return self._declaration

    # ── transport helpers ──────────────────────────────────────────────────────

    def _headers(self, idempotency_key: str | None = None) -> dict[str, str]:
        headers = {
            "Authorization": f"Bearer {self._api_key}",
            "Stripe-Version": self._declaration["api_version"],
            "Content-Type": "application/x-www-form-urlencoded",
        }
        if idempotency_key is not None:
            headers["Idempotency-Key"] = idempotency_key
        return headers

    # ── protocol operations ────────────────────────────────────────────────────

    def dispatch(self, order: DispatchOrder, deadline_s: float) -> DispatchResult:
        if order.effect_type != _EFFECT_TYPE:
            raise CapabilityUnsupported(
                f"adapter {self.adapter_id} supports {_EFFECT_TYPE!r}, not "
                f"{order.effect_type!r}"
            )
        amount = order.payload.get("amount")
        currency = order.payload.get("currency")
        if isinstance(amount, bool) or not isinstance(amount, int) or amount <= 0:
            raise CapabilityUnsupported("Stripe amount must be a positive integer")
        if (
            not isinstance(currency, str)
            or len(currency) != 3
            or not currency.isascii()
            or not currency.isalpha()
        ):
            raise CapabilityUnsupported("Stripe currency must be a three-letter code")
        extra = order.payload.get("extra", {})
        if not isinstance(extra, dict):
            raise CapabilityUnsupported("Stripe extra parameters must be an object")
        for raw_key in extra:
            key = str(raw_key)
            if (
                key in _RESERVED_EXTRA_KEYS
                or key == "metadata"
                or key.startswith("metadata[irrevon_ref]")
            ):
                raise CapabilityUnsupported(
                    f"Stripe extra parameter {key!r} is authority-sensitive or "
                    "identity-reserved"
                )
        form = {
            "amount": str(amount),
            "currency": currency.lower(),
            "metadata[irrevon_ref]": order.client_ref,
        }
        for key, value in extra.items():
            form[str(key)] = str(value)
        evidence: dict[str, Any] = {
            "adapter_id": self.adapter_id,
            "client_ref": order.client_ref,
            "request_digest": canonical_digest(
                {"effect_type": order.effect_type, "form_digest": canonical_digest(form)}
            ),
        }
        try:
            response = self._transport(
                "POST",
                f"{self._base}/v1/payment_intents",
                form,
                self._headers(idempotency_key=order.client_ref),
                deadline_s,
            )
        except WireDropped:
            return DispatchResult(
                "LOST", evidence={**evidence, "send_state": "sent_no_response"}
            )
        except TimeoutError:
            return DispatchResult(
                "TIMEOUT", evidence={**evidence, "deadline_s": deadline_s}
            )
        return self._classify(response, evidence)

    def _classify(
        self, response: HttpResponse, evidence: dict[str, Any]
    ) -> DispatchResult:
        status = response.status
        body = response.body
        digest = canonical_digest(body)
        response_headers = response.selected_headers(
            "Idempotent-Replayed",
            "Request-Id",
            "Retry-After",
            "Stripe-Rate-Limited-Reason",
            "Stripe-Should-Retry",
        )
        header_evidence = (
            {"response_headers": response_headers} if response_headers else {}
        )
        if status == 200 and isinstance(body.get("id"), str):
            return DispatchResult(
                "OK",
                destination_ref=body["id"],
                response_digest=digest,
                evidence={**evidence, "status": status, **header_evidence},
            )
        error = body.get("error", {}) if isinstance(body.get("error"), dict) else {}
        error_type = error.get("type")
        if status == 429 and "stripe-rate-limited-reason" in response_headers:
            # Stripe documents this header as the discriminator for a true
            # limiter response. A headerless 429 can be a different condition
            # (for example a lock timeout) and therefore remains ambiguous.
            return DispatchResult(
                "FAILED", failure_kind="RETRYABLE", response_digest=digest,
                evidence={
                    **evidence,
                    "status": status,
                    "throttled": True,
                    **header_evidence,
                },
            )
        if status in (400, 402, 409) and error_type in _TERMINAL_ERROR_TYPES:
            # Declaration-cited recognized rejections (side-effect-free).
            return DispatchResult(
                "FAILED", failure_kind="TERMINAL", response_digest=digest,
                evidence={
                    **evidence,
                    "status": status,
                    "error_type": error_type,
                    **header_evidence,
                },
            )
        # 5xx, unknown shapes, unexpected statuses: never optimistically FAILED.
        return DispatchResult(
            "LOST", response_digest=digest,
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
        try:
            if destination_ref is not None:
                response = self._transport(
                    "GET",
                    f"{self._base}/v1/payment_intents/{destination_ref}",
                    None, self._headers(), deadline_s,
                )
                status, body = response.status, response.body
                if status == 200 and isinstance(body.get("id"), str):
                    return StatusAnswer(
                        "PRESENT", 1, (body["id"],),
                        {"status": status, "response_digest": canonical_digest(body)},
                    )
                if status == 404 and body.get("error", {}).get("code") == "resource_missing":
                    return StatusAnswer(
                        "ABSENT", 0, (), {"status": status, "authoritative_absent": True}
                    )
                return StatusAnswer("INDETERMINATE", None, (), {"status": status})
            if client_ref is not None:
                # Search is the ONLY metadata query; it is not read-after-write
                # safe — the declaration's settlement lag calibrates absence.
                query = f'metadata["irrevon_ref"]:"{client_ref}"'
                response = self._transport(
                    "GET",
                    f"{self._base}/v1/payment_intents/search?"
                    + f"query={query}".replace('"', "%22").replace(" ", "%20"),
                    None, self._headers(), deadline_s,
                )
                status, body = response.status, response.body
                if status != 200 or not isinstance(body.get("data"), list):
                    return StatusAnswer("INDETERMINATE", None, (), {"status": status})
                refs = tuple(
                    item["id"] for item in body["data"] if isinstance(item.get("id"), str)
                )
                if refs:
                    return StatusAnswer(
                        "PRESENT", len(refs), refs,
                        {"status": status, "response_digest": canonical_digest(body)},
                    )
                return StatusAnswer(
                    "ABSENT", 0, (),
                    {"status": status, "authoritative_absent": True,
                     "via": "search-with-declared-lag"},
                )
            raise ValueError("status_query needs client_ref or destination_ref")
        except (WireDropped, TimeoutError) as err:
            return StatusAnswer(
                "INDETERMINATE", None, (), {"transport_error": type(err).__name__}
            )

    def list_effects(
        self, window_from: str, window_to: str, deadline_s: float = 10.0
    ) -> list[dict[str, Any]]:
        if not self._declaration["list_queryable"]:  # pragma: no cover
            raise CapabilityUnsupported("declaration says list_queryable=false")
        from datetime import datetime

        gte = int(datetime.fromisoformat(window_from.replace("Z", "+00:00")).timestamp())
        lte = int(datetime.fromisoformat(window_to.replace("Z", "+00:00")).timestamp())
        out: list[dict[str, Any]] = []
        starting_after: str | None = None
        for _ in range(100):  # pagination hard stop
            url = (
                f"{self._base}/v1/payment_intents?limit=100"
                f"&created[gte]={gte}&created[lte]={lte}"
            )
            if starting_after:
                url += f"&starting_after={starting_after}"
            response = self._transport("GET", url, None, self._headers(), deadline_s)
            status, body = response.status, response.body
            if status != 200 or not isinstance(body.get("data"), list):
                raise CapabilityUnsupported(f"list failed with status {status}")
            for item in body["data"]:
                out.append(
                    {
                        "destination_ref": item.get("id"),
                        "effect_type": "payment_intent",
                        "client_ref": (item.get("metadata") or {}).get("irrevon_ref"),
                        "created_at": item.get("created"),
                        "status": item.get("status"),
                    }
                )
            if not body.get("has_more") or not body["data"]:
                return out
            starting_after = body["data"][-1].get("id")
        raise CapabilityUnsupported("pagination exceeded the hard stop")
