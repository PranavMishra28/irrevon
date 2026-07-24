"""Shared HTTPS transport for real provider adapters (ADR-0034, proposed).

Transport discipline (RFC-002 §10 applied at the wire):

- One function call = one wire attempt; NO internal retries ever (hidden
  retries corrupt attempt accounting and manufacture duplicates on C2).
- Connection drops / resets / truncations raise :class:`WireDropped`
  (committed-ness unknown ⇒ the dispatcher records LOST ⇒ AMBIGUOUS).
- Deadline expiry raises :class:`TimeoutError` (⇒ TIMEOUT ⇒ AMBIGUOUS).
- HTTP error statuses are RETURNED, not raised — classification into
  FAILED/LOST is the adapter's declaration-cited job, never the transport's.
- Credentials arrive as an opaque bearer/basic header value resolved by the
  factory from an ENVIRONMENT VARIABLE NAME (never a file, never logged);
  the transport never echoes headers into errors or evidence.

Tests inject a fake transport (clearly labeled synthetic); the real
transport is exercised only in credential-gated integration runs that are
human-authorized (ToS + spike approval per ADR-0010/0012).
"""

from __future__ import annotations

import http.client
import json
import math
import urllib.error
import urllib.parse
import urllib.request
from collections.abc import Callable
from dataclasses import dataclass, field
from typing import Any

from irrevon.adapters.refdest import WireDropped

__all__ = ["HttpResponse", "Transport", "urllib_transport"]

_MAX_REQUEST_BYTES = 256 * 1024
_MAX_RESPONSE_BYTES = 1024 * 1024
_MAX_RESPONSE_DEPTH = 64
_MAX_RESPONSE_NODES = 50_000
_MAX_SAFE_INTEGER = 2**53 - 1


@dataclass(frozen=True, slots=True)
class HttpResponse:
    """One complete HTTP response with case-insensitive, evidence-selectable headers.

    Adapters retain only an explicit header allowlist in ledger evidence. Keeping
    headers available here is nevertheless required to distinguish, for example,
    a Stripe rate-limit 429 from another 429 shape without logging credentials or
    the full response envelope.
    """

    status: int
    body: dict[str, Any]
    headers: dict[str, str] = field(default_factory=dict)

    def selected_headers(self, *names: str) -> dict[str, str]:
        normalized = {key.lower(): value for key, value in self.headers.items()}
        return {
            name.lower(): normalized[name.lower()]
            for name in names
            if name.lower() in normalized
        }


# (method, url, form_or_json_body, headers, deadline_s) -> complete response
Transport = Callable[
    [str, str, dict[str, Any] | None, dict[str, str], float], HttpResponse
]


class _NoRedirect(urllib.request.HTTPRedirectHandler):
    """Return redirect responses to the adapter; never forward credentials."""

    def redirect_request(
        self,
        req: urllib.request.Request,
        fp: Any,
        code: int,
        msg: str,
        headers: Any,
        newurl: str,
    ) -> None:
        return None


def _read_bounded(response: Any) -> bytes:
    payload: bytes = response.read(_MAX_RESPONSE_BYTES + 1)
    if len(payload) > _MAX_RESPONSE_BYTES:
        return b'{"unparseable_body":true,"reason":"response_too_large"}'
    return payload


def _parse_object(payload: bytes) -> dict[str, Any]:
    if not payload:
        return {}

    def _reject_constant(value: str) -> None:
        raise ValueError(f"non-I-JSON number {value}")

    try:
        parsed = json.loads(
            payload.decode("utf-8"),
            parse_constant=_reject_constant,
        )
    except (
        UnicodeDecodeError,
        json.JSONDecodeError,
        OverflowError,
        RecursionError,
        ValueError,
    ):
        return {"unparseable_body": True}
    if not isinstance(parsed, dict):
        return {"unparseable_body": True, "reason": "top_level_not_object"}

    # Provider JSON remains untrusted after syntactic parsing. Validate the
    # domain non-recursively before adapters hash or inspect it: RFC 8785
    # rejects non-finite numbers and deeply nested values can otherwise raise
    # RecursionError during canonicalization.
    stack: list[tuple[object, int]] = [(parsed, 0)]
    nodes = 0
    while stack:
        current, depth = stack.pop()
        nodes += 1
        if nodes > _MAX_RESPONSE_NODES or depth > _MAX_RESPONSE_DEPTH:
            return {"unparseable_body": True, "reason": "invalid_json_domain"}
        if isinstance(current, dict):
            try:
                for key in current:
                    key.encode("utf-8")
            except UnicodeEncodeError:
                return {"unparseable_body": True, "reason": "invalid_json_domain"}
            stack.extend((child, depth + 1) for child in current.values())
        elif isinstance(current, list):
            stack.extend((child, depth + 1) for child in current)
        elif isinstance(current, str):
            try:
                current.encode("utf-8")
            except UnicodeEncodeError:
                return {"unparseable_body": True, "reason": "invalid_json_domain"}
        elif isinstance(current, bool) or current is None:
            continue
        elif isinstance(current, int):
            if not -_MAX_SAFE_INTEGER <= current <= _MAX_SAFE_INTEGER:
                return {"unparseable_body": True, "reason": "invalid_json_domain"}
        elif isinstance(current, float):
            if not math.isfinite(current):
                return {"unparseable_body": True, "reason": "invalid_json_domain"}
        else:  # json.loads should make this unreachable; keep the boundary closed.
            return {"unparseable_body": True, "reason": "invalid_json_domain"}
    return parsed


def urllib_transport(
    method: str,
    url: str,
    body: dict[str, Any] | None,
    headers: dict[str, str],
    deadline_s: float,
) -> HttpResponse:
    """The real wire. Encoding: form-encoded when the caller sets the
    form content type (Stripe v1), JSON otherwise.

    Provider credentials are sent only to an explicit HTTPS origin. Redirects
    are returned as ordinary status responses and never followed. Bodies are
    bounded before parsing; malformed JSON becomes a conservative unknown
    response shape rather than an exception that can terminate the worker.
    """
    parsed_url = urllib.parse.urlsplit(url)
    if parsed_url.scheme != "https" or not parsed_url.hostname:
        raise ValueError("provider transport requires an absolute HTTPS URL")
    if (
        isinstance(deadline_s, bool)
        or not isinstance(deadline_s, (int, float))
        or not math.isfinite(deadline_s)
        or deadline_s <= 0
    ):
        raise ValueError("provider transport deadline must be positive")
    request_headers = dict(headers)
    data: bytes | None = None
    if body is not None:
        if request_headers.get("Content-Type") == "application/x-www-form-urlencoded":
            data = urllib.parse.urlencode(body, doseq=True).encode()
        else:
            data = json.dumps(body, separators=(",", ":")).encode()
            request_headers.setdefault("Content-Type", "application/json")
        if len(data) > _MAX_REQUEST_BYTES:
            raise ValueError("provider request exceeds the 256 KiB limit")
    request = urllib.request.Request(
        url, data=data, headers=request_headers, method=method
    )
    opener = urllib.request.build_opener(_NoRedirect)
    try:
        with opener.open(request, timeout=deadline_s) as response:
            payload = _read_bounded(response)
            return HttpResponse(
                response.status,
                _parse_object(payload),
                dict(response.headers.items()),
            )
    except urllib.error.HTTPError as err:
        raw = _read_bounded(err)
        return HttpResponse(err.code, _parse_object(raw), dict(err.headers.items()))
    except TimeoutError:
        raise
    except (
        urllib.error.URLError,
        ConnectionError,
        OSError,
        http.client.HTTPException,
    ) as err:
        # Committed-ness unknown: the response never arrived intact.
        raise WireDropped(committed=False) from err
