"""Clean-shutdown contracts for the loopback-only synthetic destination."""

from __future__ import annotations

import os
import selectors
import signal
import subprocess
import sys
from pathlib import Path
from typing import Any

import pytest

from irrevon.adapters import refdest_server

REPO_ROOT = Path(__file__).resolve().parents[2]


def test_main_closes_server_after_keyboard_interrupt(
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    class InterruptingServer:
        server_address = ("127.0.0.1", 48123)

        def __init__(self) -> None:
            self.closed = False

        def serve_forever(self) -> None:
            raise KeyboardInterrupt

        def server_close(self) -> None:
            self.closed = True

    server = InterruptingServer()

    def make_server(*_args: Any, **_kwargs: Any) -> InterruptingServer:
        return server

    monkeypatch.setattr(refdest_server, "ThreadingHTTPServer", make_server)
    monkeypatch.setattr(sys, "argv", ["refdest_server", "--port", "0"])

    refdest_server.main()

    assert server.closed is True
    assert capsys.readouterr().out == "REFDEST READY 48123\n"


@pytest.mark.skipif(os.name == "nt", reason="SIGINT subprocess contract is POSIX-specific")
def test_process_exits_cleanly_on_sigint() -> None:
    proc = subprocess.Popen(
        [
            sys.executable,
            "-m",
            "irrevon.adapters.refdest_server",
            "--port",
            "0",
        ],
        cwd=REPO_ROOT,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
    )
    try:
        assert proc.stdout is not None
        selector = selectors.DefaultSelector()
        selector.register(proc.stdout, selectors.EVENT_READ)
        assert selector.select(timeout=10), "reference destination did not become ready"
        ready = proc.stdout.readline().strip()
        assert ready.startswith("REFDEST READY ")

        proc.send_signal(signal.SIGINT)
        stdout, stderr = proc.communicate(timeout=10)

        assert proc.returncode == 0
        assert stdout == ""
        assert stderr == ""
        assert "Traceback" not in stderr
        assert "KeyboardInterrupt" not in stderr
    finally:
        if proc.poll() is None:
            proc.kill()
            proc.communicate(timeout=10)
