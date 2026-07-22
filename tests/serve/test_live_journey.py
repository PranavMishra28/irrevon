"""The live E2E foundation, proven end-to-end in-repo: a REAL ``irrevon demo``
run (SIGKILL and all) seeds the kept database, a REAL ``irrevon serve``
subprocess serves it, and the flagship evidence comes back over HTTP.

WEB's Playwright suite consumes the identical contract via
``tests/serve/live_server.py`` (``make serve-live``); this test locks that
contract from the Python side so the joint ``web-e2e-live`` proof at
consolidation is an integration, not a first contact."""

from __future__ import annotations

import json
import os
import signal
import subprocess
import sys
import urllib.error
import urllib.request
from collections.abc import Iterator
from pathlib import Path
from typing import Any

import pytest

from tests.serve.conftest import ADMIN_DSN, FLAGSHIP_EFFECT_ID

pytestmark = pytest.mark.integration

REPO_ROOT = Path(__file__).parent.parent.parent


@pytest.fixture(scope="module")
def live_serve(tmp_path_factory: pytest.TempPathFactory) -> Iterator[dict[str, Any]]:
    """demo --keep (seed 42) + serve, via the launcher script; yields the
    parsed ready line (url, port, read_role, workbench_assets, demo_artifact).
    """
    artifact = tmp_path_factory.mktemp("live") / "demo-artifact.json"
    env = {
        **os.environ,
        "IRREVON_TEST_ADMIN_DSN": ADMIN_DSN,
        "IRREVON_LIVE_ARTIFACT": str(artifact),
        "IRREVON_LIVE_PORT": "0",
    }
    proc = subprocess.Popen(
        [sys.executable, str(REPO_ROOT / "tests" / "serve" / "live_server.py")],
        stdout=subprocess.PIPE,
        stderr=subprocess.DEVNULL,
        text=True,
        env=env,
        cwd=REPO_ROOT,
    )
    assert proc.stdout is not None
    line = proc.stdout.readline()  # blocks until demo finished + serve ready
    if not line:
        proc.wait(timeout=10)
        pytest.fail(f"live_server produced no ready line (exit {proc.returncode})")
    ready: dict[str, Any] = json.loads(line)
    try:
        yield ready
    finally:
        proc.send_signal(signal.SIGINT)
        assert proc.wait(timeout=30) == 0, "serve must exit 0 on SIGINT"


def _get(url: str) -> tuple[int, dict[str, str], bytes]:
    request = urllib.request.Request(url)
    with urllib.request.urlopen(request, timeout=30) as resp:
        return resp.status, {k.lower(): v for k, v in resp.headers.items()}, resp.read()


def test_ready_line_contract(live_serve: dict[str, Any]) -> None:
    assert live_serve["schema_version"] == "1"
    assert live_serve["url"] == f"http://127.0.0.1:{live_serve['port']}/"
    assert live_serve["read_role"] == "irrevon_read"
    assert live_serve["demo_artifact"] is True  # demo wrote it before serve


def test_flagship_effect_served_from_the_live_ledger(
    live_serve: dict[str, Any],
) -> None:
    base = live_serve["url"].rstrip("/")
    status, headers, body = _get(f"{base}/api/v1/effects")
    assert status == 200
    assert headers["irrevon-schema-version"] == "1"
    ids = [item["record"]["effect_id"] for item in json.loads(body)["data"]]
    assert FLAGSHIP_EFFECT_ID in ids, (
        "the deterministic flagship id must come from the REAL demo ledger"
    )

    status, _, body = _get(f"{base}/api/v1/effects/{FLAGSHIP_EFFECT_ID}/inspect")
    assert status == 200
    inspect = json.loads(body)
    assert inspect["classification"] == "CONFIRMED_UNIQUE"
    assert inspect["integrity"]["matches"] is True
    # The SIGKILL timeline and the dedup deny, driven by the live ledger:
    causes = [t["cause"] for t in inspect["timeline"]]
    assert "receipt_lost" in causes and "reconciled_present" in causes
    assert [d["outcome"] for d in inspect["gate_decisions"]] == ["ALLOW", "DENY"]
    assert inspect["gate_decisions"][1]["deny_check"] == "dedup"


def test_demo_artifact_route_serves_the_run_transcript(
    live_serve: dict[str, Any],
) -> None:
    base = live_serve["url"].rstrip("/")
    status, _, body = _get(f"{base}/api/v1/demo/artifact")
    assert status == 200
    artifact = json.loads(body)
    assert artifact["summary"]["contrast_holds"] is True
    events = [e["event"] for e in artifact["events"]]
    assert "crash" in events and "duplicate_rejected" in events
    assert artifact["summary"]["b5_leg"]["destination_effects"] == 2


def test_health_reports_green_over_the_live_db(live_serve: dict[str, Any]) -> None:
    base = live_serve["url"].rstrip("/")
    status, _, body = _get(f"{base}/api/v1/health")
    assert status == 200
    health = json.loads(body)
    assert health["ok"] is True
    by_name = {c["name"]: c for c in health["checks"]}
    assert by_name["serve_ready"]["status"] in ("ok", "warn")


def test_root_serves_workbench_or_honest_degrade(
    live_serve: dict[str, Any],
) -> None:
    base = live_serve["url"].rstrip("/")
    request = urllib.request.Request(f"{base}/")
    try:
        with urllib.request.urlopen(request, timeout=30) as resp:
            status, body = resp.status, resp.read()
    except urllib.error.HTTPError as err:
        status, body = err.code, err.read()
    if live_serve["workbench_assets"]:
        assert status == 200
        assert b"<!doctype html>" in body.lower()
    else:
        assert status == 503
        assert b"workbench assets not built" in body
