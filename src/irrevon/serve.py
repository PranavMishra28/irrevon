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

_EFFECT_ROUTE = re.compile(r"^/api/v1/effects/([0-9a-f]{64})(/inspect)?$")

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
# E2E-enforced on the workbench side).
_CSP = (
    "default-src 'self'; img-src 'self' data:; "
    "style-src 'self' 'unsafe-inline'; connect-src 'self'"
)

_DEGRADE_HTML = (
    "<!doctype html><html><head><title>irrevon serve</title></head><body>"
    "<h1>workbench assets not built</h1>"
    "<p>run <code>make web-build dist-stage</code>, or install from a wheel. "
    "The API under <code>/api/v1/</code> is serving normally.</p>"
    "</body></html>"
)


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
            payload = doctor_payload(self.config, read_only=True)
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

    def _log_request(self, status: int, duration_ms: float | None = None) -> None:
        if self._app().quiet:
            return
        # Identifier privacy (RFC-002 §11): the path carries only
        # Irrevon-minted ids; query VALUES are never logged.
        emit(
            "serve.request",
            method=self.command,
            path=urlsplit(self.path).path,
            status=status,
            duration_ms=round(duration_ms, 2) if duration_ms is not None else None,
        )

    def log_message(self, format: str, *args: Any) -> None:
        """Suppress the default stderr access log (serve.request JSONL owns it)."""

    def _send_common_headers(
        self, content_type: str, length: int, *, api: bool, cache: str = "no-store"
    ) -> None:
        self.send_header("Content-Type", content_type)
        self.send_header("Content-Length", str(length))
        self.send_header("X-Content-Type-Options", "nosniff")
        self.send_header("Cache-Control", cache)
        if api:
            self.send_header(SCHEMA_VERSION_HEADER, SCHEMA_VERSION)
        if content_type.startswith("text/html"):
            self.send_header("Content-Security-Policy", _CSP)

    def _send_json(
        self, status: int, payload: dict[str, Any], *, include_body: bool
    ) -> int:
        body = json.dumps(payload, default=str).encode("utf-8")
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
                        conn, effect_id, reveal=True
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
            return self._send_json(200, app.health_payload(), include_body=include_body)
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
        except psycopg.OperationalError as err:
            return self._send_json(
                503,
                _error_envelope(
                    "storage_unavailable",
                    f"ledger unreachable: {err}",
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
        if not isinstance(loaded, dict):
            return self._send_json(
                404,
                _error_envelope(
                    "not_found",
                    "demo artifact not found — run `irrevon demo` "
                    "(it writes the artifact file on completion)",
                ),
                include_body=include_body,
            )
        return self._send_json(200, loaded, include_body=include_body)

    # ── static workbench serving (ADR-0018 mechanics) ─────────────────────────

    def _static(self, path: str, include_body: bool) -> int:
        root = self._app().assets
        if root is None:
            body = _DEGRADE_HTML.encode("utf-8")
            self.send_response(503)
            self._send_common_headers("text/html; charset=utf-8", len(body), api=False)
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
        self._send_common_headers(content_type, len(body), api=False, cache=cache)
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
