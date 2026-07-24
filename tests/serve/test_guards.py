"""Serve guard tests — the three read-only layers and the version handshake.

No database required: these exercise the HTTP layer (layer 1), the bind
discipline, and the envelope/handshake contract. The DB-privilege layer
(layer 2) and session layer (layer 3) are integration-tested in
``test_readonly_role.py`` — the guarantees are TESTED, not asserted.
"""

from __future__ import annotations

from pathlib import Path

import pytest

import irrevon.serve as serve_module
from irrevon import SCHEMA_VERSION
from irrevon.cli import main
from irrevon.serve import ServeApp, create_server
from tests.serve.conftest import RunningServer, _app

ALL_API_ROUTES = [
    "/api/v1/effects",
    "/api/v1/effects/" + "0" * 64,
    "/api/v1/effects/" + "0" * 64 + "/inspect",
    "/api/v1/findings",
    "/api/v1/bench-runs",
    "/api/v1/adapters",
    "/api/v1/health",
    "/api/v1/demo/artifact",
]

WRITE_METHODS = ["POST", "PUT", "PATCH", "DELETE", "OPTIONS", "TRACE"]


# ── bind discipline (loopback-only, §1.2) ─────────────────────────────────────


def test_default_bind_is_loopback(tmp_path: Path) -> None:
    server = create_server(_app("postgresql://x@127.0.0.1:1/x", tmp_path / "a"), 0)
    try:
        assert server.socket.getsockname()[0] == "127.0.0.1"
    finally:
        server.server_close()


def test_non_loopback_bind_is_refused(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    """The post-bind assertion is the tested control: even if the bind target
    were somehow changed, the server refuses to start on non-loopback."""
    monkeypatch.setattr(serve_module, "_BIND_HOST", "0.0.0.0")
    app = _app("postgresql://x@127.0.0.1:1/x", tmp_path / "a")
    with pytest.raises(RuntimeError, match="loopback-only"):
        create_server(app, 0)


@pytest.mark.parametrize("route", ["/", *ALL_API_ROUTES])
def test_host_header_blocks_dns_rebinding(
    local_server: RunningServer, route: str
) -> None:
    status, headers, body = local_server.request(
        "GET", route, headers={"Host": "attacker.invalid"}
    )
    assert status == 421
    assert headers["cross-origin-resource-policy"] == "same-origin"
    import json

    assert json.loads(body)["error"]["code"] == "host_rejected"


def test_no_host_flag_exists(capsys: pytest.CaptureFixture[str]) -> None:
    """The option to bind elsewhere does not exist — stronger than validating
    it. argparse rejects --host as an unknown argument (usage error, exit 2)."""
    with pytest.raises(SystemExit) as excinfo:
        main(["serve", "--host", "0.0.0.0"])
    assert excinfo.value.code == 2
    assert "--host" in capsys.readouterr().err


# ── method discipline (read-only layer 1) ─────────────────────────────────────


@pytest.mark.parametrize("method", WRITE_METHODS)
def test_every_non_get_method_is_405(local_server: RunningServer, method: str) -> None:
    for route in [*ALL_API_ROUTES, "/", "/effects/deadbeef"]:
        status, headers, body = local_server.request(method, route)
        assert status == 405, f"{method} {route} → {status}"
        assert headers["allow"] == "GET, HEAD"
        import json

        envelope = json.loads(body)
        assert envelope["error"]["code"] == "method_not_allowed"
        assert envelope["schema_version"] == SCHEMA_VERSION


def test_invented_method_is_405_too(local_server: RunningServer) -> None:
    status, headers, _ = local_server.request("FROBNICATE", "/api/v1/effects")
    assert status == 405
    assert headers["allow"] == "GET, HEAD"


def test_head_is_allowed_and_bodyless(local_server: RunningServer) -> None:
    status, headers, body = local_server.request("HEAD", "/api/v1/bench-runs")
    assert status == 200
    assert body == b""
    assert int(headers["content-length"]) > 0


# ── version handshake (§2.10) ─────────────────────────────────────────────────


def test_version_header_on_success_and_errors(local_server: RunningServer) -> None:
    # success (no DB needed)
    status, headers, payload = local_server.get_json("/api/v1/bench-runs")
    assert status == 200
    assert headers["irrevon-schema-version"] == SCHEMA_VERSION
    assert payload["schema_version"] == SCHEMA_VERSION
    # 404 error
    status, headers, payload = local_server.get_json("/api/v1/no-such-route")
    assert status == 404
    assert headers["irrevon-schema-version"] == SCHEMA_VERSION
    assert payload["error"]["code"] == "not_found"
    # 405 error
    status, headers, _ = local_server.request("POST", "/api/v1/effects")
    assert status == 405
    assert headers["irrevon-schema-version"] == SCHEMA_VERSION


def test_health_serves_the_doctor_document_even_without_db(
    local_server: RunningServer,
) -> None:
    status, headers, payload = local_server.get_json("/api/v1/health")
    assert status == 503
    assert headers["irrevon-schema-version"] == SCHEMA_VERSION
    assert payload["schema_version"] == SCHEMA_VERSION
    names = [c["name"] for c in payload["checks"]]
    assert "identity_selftest" in names
    assert "serve_ready" in names  # the new check rides the shared producer
    assert payload["ok"] is False  # DB is unreachable here — honest failure


# ── DB-backed routes fail honestly without storage ────────────────────────────


def test_db_routes_map_unreachable_storage_to_503(
    local_server: RunningServer,
) -> None:
    for route in ("/api/v1/effects", "/api/v1/findings",
                  "/api/v1/effects/" + "0" * 64):
        status, _, payload = local_server.get_json(route)
        assert status == 503, route
        assert payload["error"]["code"] == "storage_unavailable"
        assert payload["error"]["retryable"] is True


# ── Q3 honesty (§2.6) ─────────────────────────────────────────────────────────


def test_bench_runs_is_honestly_empty(local_server: RunningServer) -> None:
    status, _, payload = local_server.get_json("/api/v1/bench-runs")
    assert status == 200
    assert payload["data"] == []
    assert payload["has_more"] is False
    assert payload["next_cursor"] is None
    assert payload["as_of"]


def test_no_bench_synthesis_path_exists() -> None:
    """Tripwire: every 'bench' in the serve module is the route constant or
    the word 'workbench' — no code path can synthesize a run."""
    source = Path(serve_module.__file__).read_text(encoding="utf-8")
    assert source.count("bench") == (
        source.count("bench-runs") + source.count("workbench")
    )


# ── zero non-configured network (§5.1 item 9) ─────────────────────────────────


def test_serve_module_has_no_outbound_client_imports() -> None:
    """serve's only network peers are the loopback listener and psycopg to the
    configured DSN: no HTTP client machinery exists in the module."""
    source = Path(serve_module.__file__).read_text(encoding="utf-8")
    for forbidden in ("urllib.request", "http.client", "import requests",
                      "import httpx", "socket.create_connection"):
        assert forbidden not in source, forbidden


# ── demo artifact (§2.8) ──────────────────────────────────────────────────────


def test_demo_artifact_absent_is_honest_404(local_server: RunningServer) -> None:
    status, _, payload = local_server.get_json("/api/v1/demo/artifact")
    assert status == 404
    assert payload["error"]["code"] == "not_found"
    assert "irrevon demo" in payload["error"]["message"]


def test_demo_artifact_served_fresh_from_file(tmp_path: Path) -> None:
    import json

    artifact = tmp_path / "artifact.json"
    app: ServeApp = _app("postgresql://x@127.0.0.1:1/x", artifact)
    from tests.serve.conftest import _start

    for running in _start(app):
        # absent → 404
        status, _, _ = running.get_json("/api/v1/demo/artifact")
        assert status == 404
        # written while serve runs → served fresh, no restart, no caching
        doc = {
            "schema_version": "1",
            "events": [{"event": "registered"}],
            "summary": {
                "schema_version": "1",
                "seed": 1,
                "irrevon_leg": {},
                "b5_leg": {},
                "contrast_holds": True,
            },
        }
        artifact.write_text(json.dumps(doc))
        status, _, payload = running.get_json("/api/v1/demo/artifact")
        assert status == 200
        assert payload == doc
        # unknown/local fields never become an HTTP export
        doc["summary"]["artifact_path"] = "/private/local/path"
        doc["summary"]["stable_ids"] = {"customer": "raw"}
        artifact.write_text(json.dumps(doc))
        status, _, payload = running.get_json("/api/v1/demo/artifact")
        assert status == 200
        assert "artifact_path" not in payload["summary"]
        assert "stable_ids" not in payload["summary"]
        # corrupted → honest 404, never a synthesized artifact
        artifact.write_text("{not json")
        status, _, payload = running.get_json("/api/v1/demo/artifact")
        assert status == 404


# ── adapters (§2.7) ───────────────────────────────────────────────────────────


def test_adapters_serves_packaged_declarations(local_server: RunningServer) -> None:
    status, _, payload = local_server.get_json("/api/v1/adapters")
    assert status == 200
    assert payload["schema_version"] == SCHEMA_VERSION
    adapters = [d["adapter"] for d in payload["data"]]
    assert "refdest-c2" in adapters
    assert payload["as_of"]
