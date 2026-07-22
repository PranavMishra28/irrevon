"""Process-orchestration harness (testing.md §3.2).

The engine runs as a REAL subprocess: in-process crash simulation runs
``finally`` blocks and driver cleanup — a graceful shutdown, which is exactly
what a crash is not. Kill = SIGKILL from the harness or a self-SIGKILL at an
armed crash point; the harness asserts exit status -9 so "the process died" is
itself an assertion. The reference destination is a separate plain subprocess
so it survives engine kills.
"""

from __future__ import annotations

import json
import os
import signal
import subprocess
import sys
import time
import urllib.parse
import urllib.request
from collections.abc import Iterator
from pathlib import Path
from typing import Any

import pytest

# Reuse the template-DB-per-test fixtures (importing makes pytest discover them).
from tests.integration.conftest import (  # noqa: F401
    DBHandles,
    fresh_db,
    fresh_db_unaudited,
    template_db,
)

REPO_ROOT = Path(__file__).parent.parent.parent
RUNNER = Path(__file__).parent / "engine_runner.py"


class RefdestControl:
    """Harness-side client for the /control plane (the adapter under test has
    no code path here)."""

    def __init__(self, base_url: str) -> None:
        self.base_url = base_url

    def _post(self, path: str, body: dict[str, Any]) -> dict[str, Any]:
        req = urllib.request.Request(
            f"{self.base_url}{path}",
            data=json.dumps(body).encode(),
            headers={"Content-Type": "application/json"},
            method="POST",
        )
        with urllib.request.urlopen(req, timeout=10) as resp:
            loaded = json.loads(resp.read() or b"{}")
            return loaded if isinstance(loaded, dict) else {}

    def _get(self, path: str) -> dict[str, Any]:
        with urllib.request.urlopen(f"{self.base_url}{path}", timeout=10) as resp:
            loaded = json.loads(resp.read() or b"{}")
            return loaded if isinstance(loaded, dict) else {}

    def schedule(self, entries: list[dict[str, Any]]) -> None:
        self._post("/control/schedule", {"entries": entries})

    def reset(self, seed: int = 42) -> None:
        self._post("/control/reset", {"seed": seed})

    def oob_create(self, effect_type: str, payload: dict[str, Any]) -> dict[str, Any]:
        return self._post("/control/oob", {"effect_type": effect_type, "payload": payload})

    def state(self) -> list[dict[str, Any]]:
        return list(self._get("/control/state")["effects"])

    def log(self) -> list[dict[str, Any]]:
        return list(self._get("/control/log")["log"])

    def effects_for_scope(self, marker: str) -> list[dict[str, Any]]:
        return [e for e in self.state() if marker in (e.get("client_ref") or "")]


@pytest.fixture
def refdest_server() -> Iterator[tuple[str, RefdestControl]]:
    proc = subprocess.Popen(
        [sys.executable, "-m", "irrevon.adapters.refdest_server", "--port", "0"],
        stdout=subprocess.PIPE,
        stderr=subprocess.DEVNULL,
        text=True,
        cwd=REPO_ROOT,
    )
    assert proc.stdout is not None
    line = proc.stdout.readline().strip()
    assert line.startswith("REFDEST READY "), f"unexpected: {line!r}"
    port = int(line.rsplit(" ", 1)[1])
    base_url = f"http://127.0.0.1:{port}"
    try:
        yield base_url, RefdestControl(base_url)
    finally:
        proc.kill()
        proc.wait(timeout=10)


class EngineProcess:
    """One engine subprocess with the sentinel protocol."""

    def __init__(
        self,
        dsn: str,
        refdest_url: str,
        *,
        env_extra: dict[str, str] | None = None,
        wait_ready: bool = True,
    ) -> None:
        env = dict(os.environ)
        env.update(
            {
                "IRREVON_DSN": dsn,
                "IRREVON_REFDEST_URL": refdest_url,
                "IRREVON_TEST_HOOKS": "1",
                "IRREVON_REREAD_GAP_S": "0",
            }
        )
        env.update(env_extra or {})
        self.proc = subprocess.Popen(
            [sys.executable, str(RUNNER)],
            stdin=subprocess.PIPE,
            stdout=subprocess.PIPE,
            stderr=None,
            text=True,
            cwd=REPO_ROOT,
            env=env,
        )
        self.sentinels: list[str] = []
        if wait_ready:
            self.wait_sentinel("READY")

    def wait_sentinel(self, prefix: str, timeout_s: float = 60.0) -> str:
        """Read stdout lines until one starts with ``prefix``. A missing
        sentinel fails the test (never hangs CI)."""
        assert self.proc.stdout is not None
        deadline = time.monotonic() + timeout_s
        while time.monotonic() < deadline:
            line = self.proc.stdout.readline()
            if not line:
                raise AssertionError(
                    f"engine died while waiting for {prefix!r} "
                    f"(exit={self.proc.poll()}, seen={self.sentinels})"
                )
            line = line.strip()
            self.sentinels.append(line)
            if line.startswith(prefix):
                return line
        raise AssertionError(f"timeout waiting for sentinel {prefix!r}")

    def send(self, command: str) -> dict[str, Any]:
        assert self.proc.stdin is not None
        self.proc.stdin.write(command + "\n")
        self.proc.stdin.flush()
        line = self.wait_sentinel("RESULT ")
        loaded = json.loads(line.removeprefix("RESULT "))
        return dict(loaded)

    def send_nowait(self, command: str) -> None:
        assert self.proc.stdin is not None
        self.proc.stdin.write(command + "\n")
        self.proc.stdin.flush()

    def kill(self) -> None:
        self.proc.kill()

    def sigkill(self) -> None:
        os.kill(self.proc.pid, signal.SIGKILL)

    def assert_died_by_sigkill(self, timeout_s: float = 30.0) -> None:
        code = self.proc.wait(timeout=timeout_s)
        assert code == -signal.SIGKILL, f"expected -SIGKILL, got {code}"

    def exit_code(self, timeout_s: float = 30.0) -> int:
        return self.proc.wait(timeout=timeout_s)

    def close(self) -> None:
        if self.proc.poll() is None:
            try:
                self.send_nowait("EXIT")
                self.proc.wait(timeout=5)
            except Exception:
                self.proc.kill()
                self.proc.wait(timeout=10)
        if self.proc.stdin:
            self.proc.stdin.close()
        if self.proc.stdout:
            self.proc.stdout.close()


@pytest.fixture
def engine_factory(
    fresh_db: DBHandles,  # noqa: F811 — pytest fixture injection by name
    refdest_server: tuple[str, RefdestControl],
) -> Iterator[Any]:
    """Factory for engine subprocesses bound to this test's database and
    refdest server; every spawned engine is cleaned up."""
    base_url, _control = refdest_server
    engines: list[EngineProcess] = []

    def spawn(
        env_extra: dict[str, str] | None = None, wait_ready: bool = True
    ) -> EngineProcess:
        engine = EngineProcess(
            fresh_db.app_dsn, base_url, env_extra=env_extra, wait_ready=wait_ready
        )
        engines.append(engine)
        return engine

    yield spawn
    for engine in engines:
        engine.close()


def contract(
    order_id: str,
    *,
    scope: str = "proc-test/prod",
    parameters: dict[str, Any] | None = None,
    effect_type: str = "order.create",
) -> str:
    from datetime import UTC, datetime

    return json.dumps(
        {
            "schema_version": "1",
            "stable_ids": {"order_id": order_id},
            "effect_type": effect_type,
            "effect_class": "IRREVERSIBLE",
            "scope": scope,
            "adapter_id": "refdest-c2",
            "parameters": parameters or {"note": "process-test"},
            "authority_ref": "auth_proc_1",
            "stamped_at": datetime.now(UTC).isoformat().replace("+00:00", "Z"),
        }
    )
