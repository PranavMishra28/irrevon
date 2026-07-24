"""Adversarial unit tests for the provider HTTP trust boundary."""

from __future__ import annotations

import http.client
import io
import math
import urllib.error
from email.message import Message
from typing import Any

import pytest

from irrevon.adapters import httpapi


class _Response:
    status = 200

    def __init__(self, body: bytes) -> None:
        self._body = io.BytesIO(body)
        self.headers = Message()
        self.headers["Content-Type"] = "application/json"

    def read(self, size: int = -1) -> bytes:
        return self._body.read(size)

    def __enter__(self) -> _Response:
        return self

    def __exit__(self, *_: Any) -> None:
        return None


class _Opener:
    def __init__(self, response: Any) -> None:
        self.response = response
        self.request: Any = None

    def open(self, request: Any, timeout: float) -> Any:
        self.request = request
        assert timeout > 0
        if isinstance(self.response, Exception):
            raise self.response
        return self.response


def test_transport_refuses_non_https_before_sending() -> None:
    with pytest.raises(ValueError, match="absolute HTTPS"):
        httpapi.urllib_transport("GET", "http://provider.invalid/path", None, {}, 1)


@pytest.mark.parametrize(
    ("body", "reason"),
    [
        (b"\xff", None),
        (b"[1,2,3]", "top_level_not_object"),
        (b'{"value":NaN}', None),
        (b'{"value":Infinity}', None),
        (b'{"value":"\\ud800"}', "invalid_json_domain"),
        (b'{"\\ud800":"value"}', "invalid_json_domain"),
        (b'{"value":9007199254740992}', "invalid_json_domain"),
        (
            b'{"value":' + b"[" * 65 + b"0" + b"]" * 65 + b"}",
            "invalid_json_domain",
        ),
        (b'{"value":' + b"9" * 5000 + b"}", None),
        (b"{" + b"x" * (1024 * 1024), "response_too_large"),
    ],
)
def test_malformed_or_oversized_success_is_conservative(
    monkeypatch: pytest.MonkeyPatch, body: bytes, reason: str | None
) -> None:
    opener = _Opener(_Response(body))
    monkeypatch.setattr(httpapi.urllib.request, "build_opener", lambda *_: opener)
    response = httpapi.urllib_transport(
        "GET", "https://provider.invalid/path", None, {"Authorization": "redacted"}, 1
    )
    assert response.body["unparseable_body"] is True
    if reason:
        assert response.body["reason"] == reason


def test_redirect_is_returned_and_never_followed(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    headers = Message()
    headers["Location"] = "https://attacker.invalid/collect"
    redirect = urllib.error.HTTPError(
        "https://provider.invalid/start",
        307,
        "redirect",
        headers,
        io.BytesIO(b"{}"),
    )
    opener = _Opener(redirect)
    monkeypatch.setattr(
        httpapi.urllib.request, "build_opener", lambda *handlers: opener
    )
    response = httpapi.urllib_transport(
        "POST",
        "https://provider.invalid/start",
        {"safe": "synthetic"},
        {"Authorization": "Bearer synthetic"},
        1,
    )
    assert response.status == 307
    assert opener.request.full_url == "https://provider.invalid/start"


def test_request_body_limit_prevents_wire_attempt(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(
        httpapi.urllib.request,
        "build_opener",
        lambda *_: pytest.fail("opener must not be built"),
    )
    with pytest.raises(ValueError, match="256 KiB"):
        httpapi.urllib_transport(
            "POST",
            "https://provider.invalid/path",
            {"payload": "x" * (256 * 1024)},
            {},
            1,
        )


@pytest.mark.parametrize("deadline", [0, -1, math.nan, math.inf, -math.inf, True])
def test_transport_refuses_non_finite_or_non_positive_deadline(deadline: Any) -> None:
    with pytest.raises(ValueError, match="deadline"):
        httpapi.urllib_transport(
            "GET", "https://provider.invalid/path", None, {}, deadline
        )


def test_transport_does_not_mutate_caller_headers(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    opener = _Opener(_Response(b"{}"))
    monkeypatch.setattr(httpapi.urllib.request, "build_opener", lambda *_: opener)
    headers = {"Authorization": "Bearer synthetic"}
    httpapi.urllib_transport(
        "POST", "https://provider.invalid/path", {"safe": True}, headers, 1
    )
    assert headers == {"Authorization": "Bearer synthetic"}
    assert opener.request.headers["Content-type"] == "application/json"


def test_truncated_http_response_maps_to_wire_drop(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    opener = _Opener(http.client.IncompleteRead(b'{"partial":'))
    monkeypatch.setattr(httpapi.urllib.request, "build_opener", lambda *_: opener)
    from irrevon.adapters.refdest import WireDropped

    with pytest.raises(WireDropped):
        httpapi.urllib_transport(
            "GET", "https://provider.invalid/path", None, {}, 1
        )
