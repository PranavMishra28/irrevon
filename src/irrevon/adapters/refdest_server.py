"""Local-server mode for the reference destination (RFC-002 §8).

A loopback-only stdlib HTTP wrapper around :class:`RefDest` so the destination
survives engine SIGKILL in the process-level fault suites (testing.md §3.4: a
plain subprocess, not a container). The ``/control/*`` prefix is the
harness-only fault/oracle plane — the adapter under test is configured with the
effect-API base URL and has no code path to it.

Run: ``python -m irrevon.adapters.refdest_server --port 0 --seed 42 --profile C2``
(prints ``REFDEST READY <port>`` on stdout).
"""

from __future__ import annotations

import argparse
import json
import time
import urllib.parse
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from typing import Any

from irrevon.adapters.refdest import RefDest, WireDropped


def _make_handler(refdest: RefDest) -> type[BaseHTTPRequestHandler]:
    class Handler(BaseHTTPRequestHandler):
        protocol_version = "HTTP/1.1"

        def log_message(self, format: str, *args: Any) -> None:
            pass  # quiet; the refdest keeps its own request log

        def _send(self, status: int, body: dict[str, Any]) -> None:
            payload = json.dumps(body).encode()
            self.send_response(status)
            self.send_header("Content-Type", "application/json")
            self.send_header("Content-Length", str(len(payload)))
            self.end_headers()
            self.wfile.write(payload)

        def _drop(self) -> None:
            # Close the socket without response bytes — the wire-drop fault.
            self.close_connection = True
            self.connection.close()

        def _read_body(self) -> dict[str, Any]:
            length = int(self.headers.get("Content-Length", "0"))
            if length == 0:
                return {}
            loaded = json.loads(self.rfile.read(length) or b"{}")
            return loaded if isinstance(loaded, dict) else {}

        def do_POST(self) -> None:
            path = urllib.parse.urlparse(self.path).path
            body = self._read_body()
            try:
                if path == "/effects":
                    status, resp, delay_ms = refdest.api_create(
                        effect_type=body.get("effect_type", ""),
                        payload=body.get("payload", {}),
                        client_ref=body.get("client_ref"),
                        idempotency_key=body.get("idempotency_key"),
                    )
                    if delay_ms:
                        time.sleep(delay_ms / 1000.0)
                    self._send(status, resp)
                elif path == "/notify":
                    status, resp, _ = refdest.api_notify(body.get("payload", {}))
                    self._send(status, resp)
                elif path == "/control/schedule":
                    refdest.control_schedule(body["entries"])
                    self._send(200, {"ok": True})
                elif path == "/control/reset":
                    refdest.control_reset(int(body.get("seed", 42)))
                    self._send(200, {"ok": True})
                elif path == "/control/oob":
                    effect = refdest.control_oob_create(
                        body.get("effect_type", "oob"), body.get("payload", {})
                    )
                    self._send(201, effect)
                else:
                    self._send(404, {"error": "not_found"})
            except WireDropped:
                self._drop()

        def do_GET(self) -> None:
            parsed = urllib.parse.urlparse(self.path)
            query = urllib.parse.parse_qs(parsed.query)
            try:
                if parsed.path == "/control/state":
                    self._send(200, {"effects": refdest.control_state()})
                elif parsed.path == "/control/log":
                    self._send(200, {"log": refdest.control_log()})
                elif parsed.path.startswith("/effects/"):
                    ref = parsed.path.removeprefix("/effects/")
                    status, resp, _ = refdest.api_get(ref)
                    self._send(status, resp)
                elif parsed.path == "/effects" and "client_ref" in query:
                    status, resp, _ = refdest.api_query_client_ref(query["client_ref"][0])
                    self._send(status, resp)
                elif parsed.path == "/effects":
                    status, resp, _ = refdest.api_list(
                        window_from=query.get("from", [""])[0],
                        window_to=query.get("to", ["9999"])[0],
                        include_all=query.get("include_all", ["false"])[0] == "true",
                    )
                    self._send(status, resp)
                else:
                    self._send(404, {"error": "not_found"})
            except WireDropped:
                self._drop()

    return Handler


def main() -> None:
    parser = argparse.ArgumentParser(description="Irrevon reference destination")
    parser.add_argument("--port", type=int, default=0)
    parser.add_argument("--seed", type=int, default=42)
    parser.add_argument("--profile", choices=("C1", "C2", "C3"), default="C2")
    parser.add_argument("--default-filter-quirk", action="store_true")
    args = parser.parse_args()
    refdest = RefDest(
        seed=args.seed,
        profile=args.profile,
        default_filter_quirk=args.default_filter_quirk,
    )
    server = ThreadingHTTPServer(
        ("127.0.0.1", args.port),
        _make_handler(refdest),  # loopback only
    )
    print(f"REFDEST READY {server.server_address[1]}", flush=True)
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        pass  # Ctrl-C is the documented clean shutdown path.
    finally:
        server.server_close()


if __name__ == "__main__":
    main()
