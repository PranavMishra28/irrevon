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

import json
import urllib.error
import urllib.parse
import urllib.request
from collections.abc import Callable
from typing import Any

from irrevon.adapters.refdest import WireDropped

__all__ = ["HttpResponse", "Transport", "urllib_transport"]

HttpResponse = tuple[int, dict[str, Any]]
# (method, url, form_or_json_body, headers, deadline_s) -> (status, body)
Transport = Callable[[str, str, dict[str, Any] | None, dict[str, str], float], HttpResponse]


def urllib_transport(
    method: str,
    url: str,
    body: dict[str, Any] | None,
    headers: dict[str, str],
    deadline_s: float,
) -> HttpResponse:
    """The real wire. Encoding: form-encoded when the caller sets the
    form content type (Stripe v1), JSON otherwise."""
    data: bytes | None = None
    if body is not None:
        if headers.get("Content-Type") == "application/x-www-form-urlencoded":
            data = urllib.parse.urlencode(body, doseq=True).encode()
        else:
            data = json.dumps(body).encode()
            headers.setdefault("Content-Type", "application/json")
    request = urllib.request.Request(url, data=data, headers=headers, method=method)
    try:
        with urllib.request.urlopen(request, timeout=deadline_s) as response:
            payload = response.read()
            return response.status, json.loads(payload) if payload else {}
    except urllib.error.HTTPError as err:
        raw = err.read()
        try:
            parsed = json.loads(raw) if raw else {}
        except json.JSONDecodeError:
            parsed = {"unparseable_body": True}
        return err.code, parsed
    except TimeoutError:
        raise
    except (urllib.error.URLError, ConnectionError, OSError) as err:
        # Committed-ness unknown: the response never arrived intact.
        raise WireDropped(committed=False) from err
