"""``irrevon serve`` — the loopback, read-only workbench server (RFC-002 §9;
serve design per the owner-ordered serve workstream; ADR-0024 proposed).

Three independent read-only layers, each with its own test in ``tests/serve/``:

1. HTTP: the handler implements ``do_GET``/``do_HEAD`` only; every other
   method maps to 405 with ``Allow: GET, HEAD``. No route reads a request
   body, ever. No write endpoint exists on this surface, ever.
2. DB privilege: every query runs as the SELECT-only ``irrevon_read`` role
   (migration 0005) — no INSERT/UPDATE/DELETE anywhere, no EXECUTE on the
   locked ledger transition functions.
3. Session: every connection opens with ``default_transaction_read_only=on``.

Bind discipline: hard-coded ``127.0.0.1``. There is no ``--host`` flag and no
env override — the option to bind elsewhere does not exist. Defense in depth:
a post-bind assertion refuses to start on any non-loopback address.

Framework: stdlib ``ThreadingHTTPServer`` — zero new runtime dependencies
(ADR-0013 thin-stack discipline). The API surface is exactly the frozen
workbench contract (``web/src/mocks/handlers.ts`` + ``types.ts``); payload
producers are shared with the CLI (``irrevon.api.readviews``,
``irrevon.cli.doctor``) so one producer exists per shape.
"""

from __future__ import annotations

import base64
import hashlib
import json
import re
import signal
import sys
import threading
import time
import webbrowser
from dataclasses import dataclass, field
from datetime import UTC, datetime
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from importlib import resources
from importlib.resources.abc import Traversable
from pathlib import Path
from typing import Any
from urllib.parse import parse_qs, unquote, urlsplit

import psycopg
from psycopg.rows import dict_row

from irrevon import SCHEMA_VERSION
from irrevon.api import readviews
from irrevon.cli.config import Config
from irrevon.logging import emit

__all__ = [
    "DEFAULT_PORT",
    "READ_ROLE",
    "SCHEMA_VERSION_HEADER",
    "ServeApp",
    "create_server",
    "read_connection",
    "read_dsn",
    "run_serve",
    "workbench_assets_root",
]

DEFAULT_PORT = 5180  # avoids 5199 (Vite dev, strictPort) and 5198 (live-boundary suite)
READ_ROLE = "irrevon_read"
SCHEMA_VERSION_HEADER = "Irrevon-Schema-Version"

# The bind target is a module constant, not a flag: loopback-only by
# construction. The post-bind assertion in create_server() is the tested
# control (tests monkeypatch this constant to prove the refusal fires).
_BIND_HOST = "127.0.0.1"

_HEALTH_CACHE_S = 5.0
_MAX_JSON_RESPONSE_BYTES = 4 * 1024 * 1024

_EFFECT_ROUTE = re.compile(r"^/api/v1/effects/([0-9a-f]{64})(/inspect)?$")
_KNOWN_API_ROUTES = {
    "/api/v1/effects",
    "/api/v1/findings",
    "/api/v1/bench-runs",
    "/api/v1/adapters",
    "/api/v1/health",
    "/api/v1/demo/artifact",
}
_INLINE_SCRIPT = re.compile(rb"<script(?:\s[^>]*)?>(.*?)</script\s*>", re.IGNORECASE | re.DOTALL)

_MIME_TYPES: dict[str, str] = {
    ".html": "text/html; charset=utf-8",
    ".js": "text/javascript; charset=utf-8",
    ".css": "text/css; charset=utf-8",
    ".svg": "image/svg+xml",
    ".json": "application/json; charset=utf-8",
    ".woff2": "font/woff2",
    ".png": "image/png",
    ".ico": "image/x-icon",
    ".txt": "text/plain; charset=utf-8",
    ".webmanifest": "application/manifest+json",
}

# Self-hosted-everything app (fonts packaged, zero external requests —
# E2E-enforced on the workbench side). ``script-src`` is completed per HTML
# response by _html_csp(): the Vite entry chunk comes from 'self', while each
# inline script receives a hash of its exact bytes. That keeps the pre-paint
# theme/density script functional without authorizing arbitrary inline code.
_CSP_DIRECTIVES = (
    "default-src 'none'",
    "base-uri 'none'",
    "object-src 'none'",
    "frame-ancestors 'none'",
    "form-action 'none'",
    "img-src 'self' data:",
    "font-src 'self'",
    "style-src 'self' 'unsafe-inline'",
    "connect-src 'self'",
    "manifest-src 'self'",
)

_PERMISSIONS_POLICY = "camera=(), geolocation=(), microphone=(), payment=(), usb=()"

_DEGRADE_HTML = (
    "<!doctype html><html><head><title>irrevon serve</title></head><body>"
    "<h1>workbench assets not built</h1>"
    "<p>run <code>make web-build dist-stage</code>, or install from a wheel. "
    "The API under <code>/api/v1/</code> is serving normally.</p>"
    "</body></html>"
)

_DEMO_EVENT_FIELDS: dict[str, tuple[str, ...]] = {
    "registered": ("effect_id", "lifecycle"),
    "dispatch_response_lost": ("effect_id", "fault", "lifecycle"),
    "crash": ("exit_status",),
    "recovered": ("recovery",),
    "settled_confirmed_unique": ("lifecycle", "classification"),
    "resynthesis_collapsed": ("effect_id", "replayed", "parameter_variant"),
    "duplicate_rejected": ("outcome", "deny_check", "decision_id"),
    "b5_response_lost": ("transport_outcome",),
    "b5_restart": (),
    "b5_retried": ("retried",),
    "b5_duplicate": ("destination_effects",),
}
_DEMO_LEG_FIELDS = {
    "irrevon_leg": (
        "destination_effects",
        "duplicate_rejected",
        "reconciled",
        "effect_id",
    ),
    "b5_leg": ("destination_effects", "duplicate_created"),
}


def _safe_demo_value(value: Any) -> Any | None:
    """Return a bounded JSON scalar/list/small recovery object, else ``None``."""
    if value is None or isinstance(value, bool) or type(value) is int:
        return value
    if isinstance(value, str) and len(value.encode("utf-8", errors="strict")) <= 1024:
        return value
    if isinstance(value, list) and len(value) <= 16:
        projected = [_safe_demo_value(item) for item in value]
        return projected if all(item is not None for item in projected) else None
    if isinstance(value, dict) and set(value) <= {"scanned", "adjudicated"}:
        if all(type(item) is int and item >= 0 for item in value.values()):
            return dict(value)
    return None


def _project_demo_artifact(loaded: Any) -> dict[str, Any] | None:
    """Project the local demo artifact onto the public, non-sensitive shape.

    In particular, generated ``artifact_path`` and ``workbench_url`` values are
    intentionally omitted, and unknown keys can never become an HTTP export.
    """
    if not isinstance(loaded, dict) or loaded.get("schema_version") != "1":
        return None
    events = loaded.get("events")
    summary = loaded.get("summary")
    if not isinstance(events, list) or len(events) > 64 or not isinstance(summary, dict):
        return None
    safe_events: list[dict[str, Any]] = []
    for raw in events:
        if not isinstance(raw, dict) or not isinstance(raw.get("event"), str):
            return None
        event_name = raw["event"]
        fields = _DEMO_EVENT_FIELDS.get(event_name)
        if fields is None:
            return None
        event: dict[str, Any] = {"event": event_name}
        for field_name in fields:
            if field_name not in raw:
                continue
            value = _safe_demo_value(raw[field_name])
            if value is None:
                return None
            event[field_name] = value
        safe_events.append(event)
    safe_summary: dict[str, Any] = {"schema_version": "1"}
    for field_name in ("seed", "contrast_holds"):
        value = _safe_demo_value(summary.get(field_name))
        if value is None:
            return None
        safe_summary[field_name] = value
    for leg_name, fields in _DEMO_LEG_FIELDS.items():
        raw_leg = summary.get(leg_name)
        if not isinstance(raw_leg, dict):
            return None
        leg: dict[str, Any] = {}
        for field_name in fields:
            if field_name not in raw_leg:
                continue
            value = _safe_demo_value(raw_leg[field_name])
            if value is None:
                return None
            leg[field_name] = value
        safe_summary[leg_name] = leg
    return {"schema_version": "1", "events": safe_events, "summary": safe_summary}


def _html_csp(body: bytes) -> str:
    """Return a closed CSP for this exact HTML representation.

    CSP hashes cover the exact UTF-8 bytes between an inline ``<script>`` and
    ``</script>``. Empty script bodies (including ordinary external-script
    elements) add no hash. The body is a packaged, trusted static artifact;
    hashing here keeps build output and the response policy inseparable, so a
    frontend formatting change cannot silently break first paint.
    """
    script_sources = ["'self'"]
    for script in _INLINE_SCRIPT.findall(body):
        if not script:
            continue
        digest = base64.b64encode(hashlib.sha256(script).digest()).decode("ascii")
        source = f"'sha256-{digest}'"
        if source not in script_sources:
            script_sources.append(source)
    return "; ".join((*_CSP_DIRECTIVES, f"script-src {' '.join(script_sources)}"))


def read_dsn(base_dsn: str) -> str:
    """The serve DSN: the configured DSN with the user swapped for the
    SELECT-only role and the session forced read-only (layers 2 + 3)."""
    return psycopg.conninfo.make_conninfo(
        base_dsn,
        user=READ_ROLE,
        connect_timeout=5,
        options="-c default_transaction_read_only=on",
    )


def read_connection(base_dsn: str) -> psycopg.Connection[dict[str, Any]]:
    """One short-lived read-only connection (open → query → close): at
    single-user loopback scale this costs ~ms and buys zero pooling code."""
    return psycopg.connect(read_dsn(base_dsn), row_factory=dict_row)


def workbench_assets_root() -> Traversable | None:
    """The packaged workbench (``irrevon/_web``) or ``None`` when absent
    (editable install, frontend never built) — serve degrades gracefully."""
    try:
        root = resources.files("irrevon") / "_web"
        if (root / "index.html").is_file():
            return root
    except (ModuleNotFoundError, FileNotFoundError):  # pragma: no cover
        return None
    return None


@dataclass
class ServeApp:
    """Shared server state: effective config, DSN, artifact path, assets."""

    config: Config
    dsn: str
    artifact_path: Path
    assets: Traversable | None
    quiet: bool = False
    _health_cache: tuple[float, dict[str, Any]] | None = field(
        default=None, init=False, repr=False
    )
    _health_lock: threading.Lock = field(
        default_factory=threading.Lock, init=False, repr=False
    )

    def health_payload(self) -> dict[str, Any]:
        """The doctor document in read-only serve mode, cached 5 s (the
        workbench polls this for the LIVE chip). Read-only mode means every
        connection the health path opens runs as ``irrevon_read`` and the
        ``ledger_write`` probe is skipped — reported honestly as
        ``not probed (read-only serve context)``. The full write probe stays
        a CLI ``irrevon doctor`` affordance (it runs as the operator)."""
        from irrevon.cli.doctor import doctor_payload

        with self._health_lock:
            now = time.monotonic()
            if self._health_cache and now - self._health_cache[0] < _HEALTH_CACHE_S:
                return self._health_cache[1]
            raw = doctor_payload(self.config, read_only=True)
            # The browser needs names and verdicts, not local paths, DSNs, or
            # database diagnostic text. Full detail remains in the explicit
            # local `irrevon doctor` command.
            payload = {
                "schema_version": raw["schema_version"],
                "ok": raw["ok"],
                "checks": [
                    {
                        "name": check["name"],
                        "status": check["status"],
                        "message": f"check {check['status']}",
                        "hint": None,
                    }
                    for check in raw["checks"]
                ],
            }
            self._health_cache = (now, payload)
            return payload


class _ServeServer(ThreadingHTTPServer):
    daemon_threads = True

    def __init__(self, address: tuple[str, int], app: ServeApp) -> None:
        self.app = app
        super().__init__(address, _Handler)


class _Handler(BaseHTTPRequestHandler):
    protocol_version = "HTTP/1.1"
    server_version = "irrevon-serve"
    sys_version = ""

    # ── method discipline (read-only layer 1) ─────────────────────────────────

    def do_GET(self) -> None:
        self._handle(include_body=True)

    def do_HEAD(self) -> None:
        self._handle(include_body=False)

    def __getattr__(self, name: str) -> Any:
        # BaseHTTPRequestHandler dispatches via getattr(self, "do_" + method):
        # EVERY method other than GET/HEAD — standard or invented — lands here
        # and is answered 405. No request body is ever read.
        if name.startswith("do_"):
            return self._method_not_allowed
        raise AttributeError(name)

    def _method_not_allowed(self) -> None:
        if not self._host_is_valid():
            self._reject_host(include_body=True)
            return
        body = json.dumps(
            _error_envelope(
                "method_not_allowed",
                f"{self.command} is not supported: this surface is read-only "
                "(GET/HEAD only; no write endpoint exists)",
            )
        ).encode("utf-8")
        self.send_response(405)
        self.send_header("Allow", "GET, HEAD")
        self._send_common_headers(
            "application/json; charset=utf-8", len(body), api=True
        )
        self.end_headers()
        self.wfile.write(body)
        self._log_request(405)

    # ── request plumbing ──────────────────────────────────────────────────────

    def _app(self) -> ServeApp:
        server = self.server
        assert isinstance(server, _ServeServer)
        return server.app

    def _handle(self, *, include_body: bool) -> None:
        started = time.monotonic()
        if not self._host_is_valid():
            status = self._reject_host(include_body=include_body)
            self._log_request(
                status, duration_ms=(time.monotonic() - started) * 1000.0
            )
            return
        split = urlsplit(self.path)
        path = unquote(split.path)
        try:
            if path == "/api" or path.startswith("/api/"):
                status = self._api(path, parse_qs(split.query), include_body)
            else:
                status = self._static(path, include_body)
        except (BrokenPipeError, ConnectionResetError):  # client went away
            return
        except Exception as err:
            status = self._send_json(
                500,
                _error_envelope("internal", f"unhandled error: {type(err).__name__}"),
                include_body=include_body,
            )
        self._log_request(status, duration_ms=(time.monotonic() - started) * 1000.0)

    def _host_is_valid(self) -> bool:
        values = self.headers.get_all("Host", failobj=[])
        server = self.server
        assert isinstance(server, _ServeServer)
        expected = f"127.0.0.1:{server.server_address[1]}"
        return len(values) == 1 and values[0] == expected

    def _reject_host(self, *, include_body: bool) -> int:
        return self._send_json(
            421,
            _error_envelope(
                "host_rejected",
                "request Host does not match the loopback listener",
            ),
            include_body=include_body,
        )

    def _log_request(self, status: int, duration_ms: float | None = None) -> None:
        if self._app().quiet:
            return
        raw_path = unquote(urlsplit(self.path).path)
        effect_match = _EFFECT_ROUTE.match(raw_path)
        if effect_match is not None:
            logged_path = "/api/v1/effects/:effect_id"
            if effect_match.group(2):
                logged_path += "/inspect"
        elif raw_path in _KNOWN_API_ROUTES:
            logged_path = raw_path
        elif raw_path.startswith("/api"):
            logged_path = "/api/unknown"
        else:
            logged_path = "/static"
        # Query values, caller-controlled unknown paths, and minted identifiers
        # are never logged.
        emit(
            "serve.request",
            method=self.command,
            path=logged_path,
            status=status,
            duration_ms=round(duration_ms, 2) if duration_ms is not None else None,
        )

    def log_message(self, format: str, *args: Any) -> None:
        """Suppress the default stderr access log (serve.request JSONL owns it)."""

    def _send_common_headers(
        self,
        content_type: str,
        length: int,
        *,
        api: bool,
        cache: str = "no-store",
        html_body: bytes | None = None,
    ) -> None:
        self.send_header("Content-Type", content_type)
        self.send_header("Content-Length", str(length))
        self.send_header("X-Content-Type-Options", "nosniff")
        self.send_header("X-Frame-Options", "DENY")
        self.send_header("Referrer-Policy", "no-referrer")
        self.send_header("Cross-Origin-Resource-Policy", "same-origin")
        self.send_header("Permissions-Policy", _PERMISSIONS_POLICY)
        self.send_header("Cache-Control", cache)
        if api:
            self.send_header(SCHEMA_VERSION_HEADER, SCHEMA_VERSION)
        if content_type.startswith("text/html"):
            if html_body is None:  # programming error: hashes must match the body
                raise RuntimeError("HTML response missing body for CSP construction")
            self.send_header("Content-Security-Policy", _html_csp(html_body))

    def _send_json(
        self, status: int, payload: dict[str, Any], *, include_body: bool
    ) -> int:
        body = _bounded_json_bytes(payload)
        if body is None:
            # Fail closed before headers or payload bytes are written. Detail
            # responses can grow with an append-only ledger; never let one
            # unpaginated representation become a partial evidence export.
            status = 500
            body = json.dumps(
                _error_envelope(
                    "response_too_large",
                    "response exceeds the serve safety limit",
                )
            ).encode("utf-8")
        self.send_response(status)
        self._send_common_headers(
            "application/json; charset=utf-8", len(body), api=True
        )
        self.end_headers()
        if include_body:
            self.wfile.write(body)
        return status

    # ── the API router (routes exactly per the frozen workbench contract) ─────

    def _api(
        self, path: str, query: dict[str, list[str]], include_body: bool
    ) -> int:
        app = self._app()
        if path == "/api/v1/effects":
            return self._db_json(
                lambda conn: readviews.list_effects(
                    conn,
                    scope=_one(query, "scope"),
                    lifecycle=query.get("lifecycle"),
                    classification=query.get("classification"),
                    effect_type=_one(query, "effect_type"),
                    effect_class=_one(query, "effect_class"),
                    time_from=_one(query, "from"),
                    time_to=_one(query, "to"),
                    limit=_one(query, "limit"),
                    cursor=_one(query, "cursor"),
                ),
                include_body,
            )
        match = _EFFECT_ROUTE.match(path)
        if match is not None:
            effect_id = match.group(1)
            if match.group(2):  # /inspect — the shared single producer
                return self._db_json(
                    lambda conn: readviews.inspect_payload(
                        conn, effect_id, reveal=False
                    ),
                    include_body,
                )
            return self._db_json(
                lambda conn: readviews.effect_item(conn, effect_id), include_body
            )
        if path == "/api/v1/findings":
            return self._db_json(
                lambda conn: readviews.list_findings(
                    conn,
                    classification=query.get("classification"),
                    resolution_status=query.get("resolution_status"),
                    subject_effect_id=_one(query, "subject_effect_id"),
                    adapter=_one(query, "adapter"),
                    destination_ref=_one(query, "destination_ref"),
                    time_from=_one(query, "from"),
                    time_to=_one(query, "to"),
                    limit=_one(query, "limit"),
                    cursor=_one(query, "cursor"),
                ),
                include_body,
            )
        if path == "/api/v1/bench-runs":
            # Honest empty, always: run-record schemas are deferred Stage-B
            # artifacts and the harness is M5+. Never synthesize a run.
            return self._send_json(
                200,
                {
                    "schema_version": SCHEMA_VERSION,
                    "data": [],
                    "has_more": False,
                    "next_cursor": None,
                    "as_of": readviews.iso(datetime.now(UTC)),
                },
                include_body=include_body,
            )
        if path == "/api/v1/adapters":
            return self._adapters(include_body)
        if path == "/api/v1/health":
            health = app.health_payload()
            return self._send_json(
                200 if health.get("ok") is True else 503,
                health,
                include_body=include_body,
            )
        if path == "/api/v1/demo/artifact":
            return self._demo_artifact(include_body)
        return self._send_json(
            404,
            _error_envelope("not_found", f"no such route: {path}"),
            include_body=include_body,
        )

    def _db_json(
        self,
        producer: Any,
        include_body: bool,
    ) -> int:
        try:
            with read_connection(self._app().dsn) as conn:
                payload = producer(conn)
        except readviews.QueryInvalid as err:
            return self._send_json(
                400,
                _error_envelope("query_invalid", str(err)),
                include_body=include_body,
            )
        except psycopg.OperationalError:
            return self._send_json(
                503,
                _error_envelope(
                    "storage_unavailable",
                    "ledger is unavailable",
                    retryable=True,
                ),
                include_body=include_body,
            )
        if payload is None:
            return self._send_json(
                404,
                _error_envelope("not_found", "no such effect"),
                include_body=include_body,
            )
        return self._send_json(200, payload, include_body=include_body)

    def _adapters(self, include_body: bool) -> int:
        from irrevon.adapters.base import declarations_dir, load_declaration

        data = [
            load_declaration(path)
            for path in sorted(declarations_dir().glob("*.capability.json"))
        ]
        return self._send_json(
            200,
            {
                "schema_version": SCHEMA_VERSION,
                "data": data,
                "as_of": readviews.iso(datetime.now(UTC)),
            },
            include_body=include_body,
        )

    def _demo_artifact(self, include_body: bool) -> int:
        # Read fresh per request — the user may re-run demo while serve runs.
        try:
            loaded = json.loads(self._app().artifact_path.read_text(encoding="utf-8"))
        except (OSError, ValueError):
            loaded = None
        projected = _project_demo_artifact(loaded)
        if projected is None:
            return self._send_json(
                404,
                _error_envelope(
                    "not_found",
                    "demo artifact not found — run `irrevon demo` "
                    "(it writes the artifact file on completion)",
                ),
                include_body=include_body,
            )
        return self._send_json(200, projected, include_body=include_body)

    # ── static workbench serving (ADR-0018 mechanics) ─────────────────────────

    def _static(self, path: str, include_body: bool) -> int:
        root = self._app().assets
        if root is None:
            body = _DEGRADE_HTML.encode("utf-8")
            self.send_response(503)
            self._send_common_headers(
                "text/html; charset=utf-8",
                len(body),
                api=False,
                html_body=body,
            )
            self.end_headers()
            if include_body:
                self.wfile.write(body)
            return 503

        segments = [seg for seg in path.split("/") if seg and seg != "."]
        for seg in segments:
            # Never a filesystem join from the raw URL: traversal segments are
            # rejected outright and resolution walks the Traversable only.
            if seg == ".." or "\0" in seg or "\\" in seg:
                return self._send_json(
                    404,
                    _error_envelope("not_found", "no such path"),
                    include_body=include_body,
                )
        node: Traversable = root
        for seg in segments:
            node = node / seg
        if segments and node.is_file():
            return self._send_file(node, "/" + "/".join(segments), include_body)
        # SPA fallback: the client router owns /effects/<id> etc.
        return self._send_file(root / "index.html", "/index.html", include_body)

    def _send_file(self, node: Traversable, norm_path: str, include_body: bool) -> int:
        suffix = norm_path[norm_path.rfind(".") :] if "." in norm_path else ""
        content_type = _MIME_TYPES.get(suffix, "application/octet-stream")
        body = node.read_bytes()
        cache = (
            "public, max-age=31536000, immutable"  # Vite content-hashed names
            if norm_path.startswith("/assets/")
            else "no-store"
        )
        self.send_response(200)
        self._send_common_headers(
            content_type,
            len(body),
            api=False,
            cache=cache,
            html_body=body if content_type.startswith("text/html") else None,
        )
        self.end_headers()
        if include_body:
            self.wfile.write(body)
        return 200


def _one(query: dict[str, list[str]], name: str) -> str | None:
    values = query.get(name)
    return values[0] if values else None


def _error_envelope(
    code: str, message: str, *, retryable: bool = False
) -> dict[str, Any]:
    """The dx-api §1.3 error envelope, HTTP-mapped (§2.10)."""
    return {
        "schema_version": SCHEMA_VERSION,
        "error": {
            "code": code,
            "message": message,
            "retryable": retryable,
            "details": {},
        },
    }


def _bounded_json_bytes(payload: dict[str, Any]) -> bytes | None:
    """Encode one JSON response without materializing bytes beyond the ceiling."""
    chunks: list[bytes] = []
    size = 0
    for chunk in json.JSONEncoder(default=str).iterencode(payload):
        encoded = chunk.encode("utf-8")
        size += len(encoded)
        if size > _MAX_JSON_RESPONSE_BYTES:
            return None
        chunks.append(encoded)
    return b"".join(chunks)


# ── server lifecycle ───────────────────────────────────────────────────────────


def create_server(app: ServeApp, port: int) -> _ServeServer:
    """Bind loopback-only and refuse anything else. ``port=0`` binds an
    ephemeral port; read the real one back from ``server.server_address``."""
    server = _ServeServer((_BIND_HOST, port), app)
    bound_host = str(server.socket.getsockname()[0])
    if bound_host != "127.0.0.1":
        server.server_close()
        raise RuntimeError(
            f"refusing to serve on non-loopback address {bound_host!r}: "
            "irrevon serve is loopback-only by design (no --host flag exists)"
        )
    return server


class _PreflightFailure(Exception):
    """A declared startup failure (exit 3), printed with a doctor-style hint."""

    def __init__(self, message: str, hint: str) -> None:
        super().__init__(message)
        self.hint = hint


def _preflight(dsn: str) -> None:
    """DB reachable as the read role; migrations current (doctor's check)."""
    from irrevon.ledger.db import migrations_dir

    try:
        with read_connection(dsn) as conn:
            applied = {
                str(row["filename"])
                for row in conn.execute(
                    "SELECT filename FROM irrevon_schema_migrations"
                ).fetchall()
            }
    except psycopg.errors.UndefinedTable as err:
        raise _PreflightFailure(
            f"migration journal missing: {err}",
            "run `irrevon init` to apply migrations",
        ) from err
    except psycopg.OperationalError as err:
        raise _PreflightFailure(
            f"ledger unreachable as {READ_ROLE}: {err}",
            "docker compose up -d --wait && irrevon init "
            "(migration 0005 creates the read role)",
        ) from err
    expected = {path.name for path in migrations_dir().glob("*.sql")}
    missing = sorted(expected - applied)
    if missing:
        raise _PreflightFailure(
            f"migrations not applied: {missing}",
            "run `irrevon init` to apply them",
        )


def run_serve(
    config: Config,
    *,
    port: int,
    demo_artifact: str,
    open_browser: bool,
    as_json: bool,
    quiet: bool,
) -> int:
    """Startup: preflight → bind → ready line → serve until SIGINT/SIGTERM.

    Exit codes (RFC-002 §12 single table): 0 clean shutdown · 1 unexpected
    crash (incl. the loopback refusal) · 2 usage · 3 preflight declared
    failure.
    """
    dsn = config.resolved_dsn()
    try:
        _preflight(dsn)
    except _PreflightFailure as failure:
        print(f"serve: {failure}", file=sys.stderr)
        print(f"       hint: {failure.hint}", file=sys.stderr)
        return 3

    assets = workbench_assets_root()
    artifact_path = Path(demo_artifact)
    app = ServeApp(
        config=config, dsn=dsn, artifact_path=artifact_path, assets=assets, quiet=quiet
    )
    try:
        server = create_server(app, port)
    except OSError as err:
        print(
            f"serve: cannot bind 127.0.0.1:{port}: {err}\n"
            "       hint: another serve or the Vite dev server may be running; "
            "pass --port",
            file=sys.stderr,
        )
        return 3

    real_port = int(server.server_address[1])
    url = f"http://127.0.0.1:{real_port}/"
    if as_json:
        # One JSON document on stdout (dx-api D2); logs go to stderr.
        print(
            json.dumps(
                {
                    "schema_version": SCHEMA_VERSION,
                    "url": url,
                    "port": real_port,
                    "read_role": READ_ROLE,
                    "workbench_assets": assets is not None,
                    "demo_artifact": artifact_path.is_file(),
                }
            ),
            flush=True,
        )
    else:
        print(url, flush=True)
        print("read-only · loopback-only · Ctrl-C to stop", file=sys.stderr)
    if assets is None and not quiet:
        print(
            "serve: workbench assets not built — API only; run "
            "`make web-build dist-stage`, or install from a wheel",
            file=sys.stderr,
        )
    if open_browser:
        webbrowser.open(url)

    def _sigterm(_signum: int, _frame: Any) -> None:
        raise KeyboardInterrupt

    previous = signal.signal(signal.SIGTERM, _sigterm)
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        pass  # clean shutdown — exit 0
    finally:
        signal.signal(signal.SIGTERM, previous)
        server.server_close()
    return 0
