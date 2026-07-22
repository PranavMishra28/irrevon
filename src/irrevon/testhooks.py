"""Fault-injection seams: crash points and sync points (testing.md §3.3).

Both are compiled into the engine at well-defined seams and are NO-OPS unless
armed. Production/default builds keep the seams so the tested binary is the
shipped binary. Arming rules (the anti-shortcut boundary):

1. Hooks arm only if ``IRREVON_TEST_HOOKS=1`` AND the process is not in
   benchmark mode; ``IRREVON_BENCH=1`` together with test hooks is a startup
   error — a benchmark run with hooks armed is INVALID by construction.
2. A crash point delivers SIGKILL to its own process: kernel-enforced,
   uncatchable, no Python-level cleanup; the in-flight Postgres transaction is
   aborted server-side when the connection drops.
3. A sync point emits ``HOOK <seam> REACHED`` on stdout and blocks until the
   harness creates the release file — used to pin interleavings without sleeps.
"""

from __future__ import annotations

import os
import signal
import sys
import time

__all__ = ["assert_arming_sane", "crashpoint", "syncpoint"]

_HIT_COUNTS: dict[str, int] = {}


def _hooks_enabled() -> bool:
    return os.environ.get("IRREVON_TEST_HOOKS") == "1"


def assert_arming_sane() -> None:
    """Startup guard: benchmark mode with test hooks armed is a hard error."""
    if _hooks_enabled() and os.environ.get("IRREVON_BENCH") == "1":
        raise RuntimeError(
            "IRREVON_TEST_HOOKS and IRREVON_BENCH are both set: fault hooks are "
            "test-only and must never arm in benchmark mode (testing.md §3.3)"
        )


def crashpoint(seam: str) -> None:
    """SIGKILL self when armed via ``IRREVON_CRASH_AT=<seam>[:<n>]`` (nth hit)."""
    if not _hooks_enabled():
        return
    assert_arming_sane()
    armed = os.environ.get("IRREVON_CRASH_AT", "")
    if not armed:
        return
    target, _, nth_raw = armed.partition(":")
    if target != seam:
        return
    nth = int(nth_raw) if nth_raw else 1
    _HIT_COUNTS[seam] = _HIT_COUNTS.get(seam, 0) + 1
    if _HIT_COUNTS[seam] >= nth:
        sys.stdout.flush()
        sys.stderr.flush()
        os.kill(os.getpid(), signal.SIGKILL)


def syncpoint(seam: str) -> None:
    """Announce and block until released when armed via
    ``IRREVON_SYNC_AT=<seam>[,<seam>…]`` + ``IRREVON_SYNC_DIR=<dir>`` (harness
    creates ``<dir>/<seam>.release`` to unblock). Hard timeout so a forgotten
    release fails the test instead of hanging CI."""
    if not _hooks_enabled():
        return
    assert_arming_sane()
    armed = {s for s in os.environ.get("IRREVON_SYNC_AT", "").split(",") if s}
    if seam not in armed:
        return
    sync_dir = os.environ.get("IRREVON_SYNC_DIR")
    if not sync_dir:
        raise RuntimeError("IRREVON_SYNC_AT armed without IRREVON_SYNC_DIR")
    print(f"HOOK {seam} REACHED", flush=True)
    release = os.path.join(sync_dir, f"{seam}.release")
    deadline = time.monotonic() + 30.0
    while not os.path.exists(release):
        if time.monotonic() > deadline:
            raise TimeoutError(f"syncpoint {seam}: release file never appeared")
        time.sleep(0.01)
