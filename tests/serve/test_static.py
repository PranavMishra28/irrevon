"""Static workbench serving: SPA fallback, traversal refusal, MIME/cache/CSP
headers, and the graceful missing-assets degrade (ADR-0018 mechanics)."""

from __future__ import annotations

import base64
import hashlib
from collections.abc import Iterator
from pathlib import Path

import pytest

from tests.serve.conftest import RunningServer, _app, _start

INLINE_SCRIPT = (
    "\n"
    'try { document.documentElement.setAttribute("data-theme", '
    'localStorage.getItem("irrevon.theme") || "light"); } catch (e) {}\n'
)
INDEX_HTML = (
    '<!doctype html><html><body><div id="root"></div>'
    f"<script>{INLINE_SCRIPT}</script>"
    '<script type="module" src="/assets/app-abc123.js"></script>'
    "</body></html>"
)


def _assert_common_security_headers(headers: dict[str, str]) -> None:
    assert headers["x-content-type-options"] == "nosniff"
    assert headers["x-frame-options"] == "DENY"
    assert headers["referrer-policy"] == "no-referrer"
    assert headers["permissions-policy"] == (
        "camera=(), geolocation=(), microphone=(), payment=(), usb=()"
    )


@pytest.fixture
def assets_server(tmp_path: Path) -> Iterator[RunningServer]:
    root = tmp_path / "web"
    (root / "assets").mkdir(parents=True)
    (root / "brand").mkdir()
    (root / "index.html").write_text(INDEX_HTML)
    (root / "assets" / "app-abc123.js").write_text("console.log(1)")
    (root / "assets" / "app-abc123.css").write_text("body{}")
    (root / "brand" / "mark.svg").write_text("<svg xmlns='http://www.w3.org/2000/svg'/>")
    (root / "secret-sibling.txt").write_text("inside root is fine")
    (tmp_path / "outside.txt").write_text("MUST NEVER BE SERVED")
    app = _app("postgresql://x@127.0.0.1:1/x", tmp_path / "a.json", assets=root)
    yield from _start(app)


def test_index_and_spa_fallback(assets_server: RunningServer) -> None:
    for path in ("/", "/effects/" + "de" * 32, "/findings", "/no/such/route"):
        status, headers, body = assets_server.request("GET", path)
        assert status == 200, path
        assert headers["content-type"].startswith("text/html")
        assert headers["cache-control"] == "no-store"
        assert "content-security-policy" in headers
        _assert_common_security_headers(headers)
        csp = headers["content-security-policy"]
        assert "default-src 'none'" in csp
        assert "base-uri 'none'" in csp
        assert "object-src 'none'" in csp
        assert "frame-ancestors 'none'" in csp
        assert "form-action 'none'" in csp
        assert body.decode() == INDEX_HTML


def test_csp_authorizes_only_the_exact_inline_script(
    assets_server: RunningServer,
) -> None:
    status, headers, _ = assets_server.request("GET", "/")
    assert status == 200
    csp = headers["content-security-policy"]
    script_directive = next(
        directive.strip()
        for directive in csp.split(";")
        if directive.strip().startswith("script-src ")
    )
    exact = base64.b64encode(hashlib.sha256(INLINE_SCRIPT.encode()).digest()).decode()
    mutated = base64.b64encode(hashlib.sha256((INLINE_SCRIPT + " ").encode()).digest()).decode()
    assert f"'sha256-{exact}'" in script_directive
    assert f"'sha256-{mutated}'" not in script_directive
    assert "'self'" in script_directive
    assert "'unsafe-inline'" not in script_directive


def test_hashed_assets_get_immutable_cache_and_mime(
    assets_server: RunningServer,
) -> None:
    status, headers, _ = assets_server.request("GET", "/assets/app-abc123.js")
    assert status == 200
    assert headers["content-type"].startswith("text/javascript")
    assert headers["cache-control"] == "public, max-age=31536000, immutable"
    _assert_common_security_headers(headers)
    assert "content-security-policy" not in headers

    status, headers, _ = assets_server.request("GET", "/assets/app-abc123.css")
    assert headers["content-type"].startswith("text/css")
    _assert_common_security_headers(headers)

    status, headers, _ = assets_server.request("GET", "/brand/mark.svg")
    assert headers["content-type"] == "image/svg+xml"
    assert headers["cache-control"] == "no-store"  # unhashed public file
    _assert_common_security_headers(headers)


@pytest.mark.parametrize(
    "attempt",
    [
        "/../pyproject.toml",
        "/../outside.txt",
        "/assets/../../etc/passwd",
        "/%2e%2e/outside.txt",
        "/assets/%2e%2e/%2e%2e/outside.txt",
        "/..%2foutside.txt",
    ],
)
def test_traversal_attempts_never_escape_the_assets_root(
    assets_server: RunningServer, attempt: str
) -> None:
    status, _, body = assets_server.request("GET", attempt)
    assert b"MUST NEVER BE SERVED" not in body
    assert status == 404, f"{attempt} → {status}"


def test_null_byte_segment_is_rejected(assets_server: RunningServer) -> None:
    status, _, body = assets_server.request("GET", "/index%00.html")
    assert status == 404
    assert b"MUST NEVER BE SERVED" not in body


def test_head_serves_headers_without_body(assets_server: RunningServer) -> None:
    status, headers, body = assets_server.request("HEAD", "/")
    assert status == 200
    assert body == b""
    assert int(headers["content-length"]) == len(INDEX_HTML.encode())


def test_missing_assets_degrade_gracefully(local_server: RunningServer) -> None:
    """No `_web` (editable install, frontend never built): serve starts, the
    API works, and non-API GETs get an honest 503 notice — never a fixture."""
    status, api_headers, payload = local_server.get_json("/api/v1/bench-runs")
    assert status == 200 and payload["data"] == []
    _assert_common_security_headers(api_headers)

    status, headers, body = local_server.request("GET", "/")
    assert status == 503
    assert headers["content-type"].startswith("text/html")
    _assert_common_security_headers(headers)
    assert "frame-ancestors 'none'" in headers["content-security-policy"]
    assert b"workbench assets not built" in body
    assert b"make web-build dist-stage" in body


def test_api_error_carries_common_security_headers(
    local_server: RunningServer,
) -> None:
    status, headers, payload = local_server.get_json("/api/v1/no-such-route")
    assert status == 404
    assert payload["error"]["code"] == "not_found"
    _assert_common_security_headers(headers)
    assert "content-security-policy" not in headers
