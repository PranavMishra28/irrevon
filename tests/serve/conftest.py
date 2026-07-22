"""Serve-suite harness: in-process servers on ephemeral ports.

Two tiers:

- ``local_server`` — no database required: a server bound to 127.0.0.1:0 with
  an unreachable DSN, for the pure HTTP-layer guards (method rejection,
  version handshake, static/traversal, honest-empty routes).
- ``seeded_server`` (integration) — a template-clone database seeded through
  the REAL engine (register/dispatch/reconcile the demo shapes), served by an
  in-process server for the Q1/Q2/inspect conformance tests.
- ``live_serve`` (integration) — the live-E2E foundation: seeds via
  ``irrevon demo --keep`` as a real subprocess and starts a real
  ``irrevon serve`` subprocess; yields the parsed ready line. WEB's Playwright
  suite consumes the same contract via ``tests/serve/live_server.py``
  (see the Makefile ``serve-live`` block).
"""

from __future__ import annotations

import http.client
import json
import threading
from collections.abc import Iterator
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

import pytest

from irrevon.cli.config import Config
from irrevon.serve import ServeApp, create_server

# Template-DB fixtures for the integration-marked tests in this package.
from tests.integration.conftest import (  # noqa: F401
    ADMIN_DSN,
    DBHandles,
    fresh_db,
    fresh_db_unaudited,
    template_db,
)

UNREACHABLE_DSN = "postgresql://nobody@127.0.0.1:1/nowhere"

FLAGSHIP_EFFECT_ID = "0bb7e8d64711e0cc5ec277fb9bb64d3d321fdd53dd92b8ebb1752fde822785f5"


@dataclass
class RunningServer:
    port: int
    app: ServeApp

    def request(
        self, method: str, path: str, *, headers: dict[str, str] | None = None
    ) -> tuple[int, dict[str, str], bytes]:
        conn = http.client.HTTPConnection("127.0.0.1", self.port, timeout=15)
        try:
            conn.request(method, path, headers=headers or {})
            resp = conn.getresponse()
            body = resp.read()
            return resp.status, {k.lower(): v for k, v in resp.getheaders()}, body
        finally:
            conn.close()

    def get_json(self, path: str) -> tuple[int, dict[str, str], Any]:
        status, headers, body = self.request("GET", path)
        return status, headers, json.loads(body) if body else None


def _start(app: ServeApp) -> Iterator[RunningServer]:
    server = create_server(app, port=0)
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    try:
        yield RunningServer(port=int(server.server_address[1]), app=app)
    finally:
        server.shutdown()
        server.server_close()
        thread.join(timeout=10)


def _app(dsn: str, artifact_path: Path, assets: Any = None) -> ServeApp:
    config = Config(path=None, dsn=dsn)
    return ServeApp(
        config=config,
        dsn=dsn,
        artifact_path=artifact_path,
        assets=assets,
        quiet=True,
    )


@pytest.fixture
def local_server(tmp_path: Path) -> Iterator[RunningServer]:
    """HTTP layer only — DB-backed routes answer 503 storage_unavailable."""
    yield from _start(_app(UNREACHABLE_DSN, tmp_path / "no-artifact.json"))


@pytest.fixture
def seeded_effect(fresh_db: DBHandles) -> tuple[DBHandles, str]:  # noqa: F811
    """One flagship-shaped effect driven through the REAL engine: response
    lost after commit → reconcile → CONFIRMED_UNIQUE → re-synthesis denied."""
    from irrevon.adapters.base import declarations_dir, load_declaration
    from irrevon.adapters.refdest import RefDest, RefdestAdapter
    from irrevon.api import Engine

    declaration = load_declaration(declarations_dir() / "refdest-c2.capability.json")
    refdest = RefDest(seed=7)
    adapter = RefdestAdapter("refdest-c2", declaration, instance=refdest)
    with Engine(fresh_db.app_dsn, {"refdest-c2": adapter}) as engine:
        engine.boot()
        reg = engine.register_intent(
            {
                "schema_version": "1",
                "stable_ids": {"order_id": "serve-9410"},
                "effect_type": "order.create",
                "effect_class": "IRREVERSIBLE",
                "scope": "serve/prod",
                "adapter_id": "refdest-c2",
                "parameters": {"line_items": [{"sku": "SKU-1", "quantity": 1}]},
                "authority_ref": "auth_serve_1",
                "stamped_at": datetime.now(UTC).isoformat().replace("+00:00", "Z"),
            }
        )
        refdest.control_schedule(
            [{"match": {"op": "create"}, "fault": "DROP_RESPONSE_AFTER_COMMIT"}]
        )
        engine.dispatch(reg.effect_id)
        engine.reconcile(reg.effect_id)
        engine.dispatch(reg.effect_id)  # gate DENY (dedup) with evidence
    return fresh_db, reg.effect_id


@pytest.fixture
def seeded_server(
    seeded_effect: tuple[DBHandles, str], tmp_path: Path
) -> Iterator[tuple[RunningServer, str]]:
    """An in-process server over the seeded database (admin DSN as the base —
    serve swaps the user for irrevon_read itself)."""
    handles, effect_id = seeded_effect
    artifact = tmp_path / "demo-artifact.json"
    artifact.write_text(
        json.dumps(
            {"schema_version": "1", "events": [{"event": "registered"}],
             "summary": {"schema_version": "1", "contrast_holds": True}}
        )
    )
    for running in _start(_app(handles.admin_dsn, artifact)):
        yield running, effect_id
