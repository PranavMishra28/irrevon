"""Environment + dependency capture (irrevonbench/environment/v1).

Captured once per run; the write-ahead run manifest pins its digest. Environment
drift between paired runs is a reportable integrity signal, not a silent
condition (preregistration §8; drift check in `bench analyze`).
"""

from __future__ import annotations

import hashlib
import os
import platform
import subprocess
import sys
from datetime import UTC, datetime
from importlib import metadata
from pathlib import Path
from typing import Any

__all__ = ["capture_environment"]

_RELEVANT_PACKAGES = ("irrevon", "jsonschema", "psycopg", "rfc8785")


def _package_versions() -> list[dict[str, str]]:
    packages = []
    for name in _RELEVANT_PACKAGES:
        try:
            packages.append({"name": name, "version": metadata.version(name)})
        except metadata.PackageNotFoundError:
            continue
    return sorted(packages, key=lambda p: p["name"])


def _lockfile_sha256() -> str | None:
    for parent in Path(__file__).resolve().parents:
        lock = parent / "uv.lock"
        if lock.is_file():
            return hashlib.sha256(lock.read_bytes()).hexdigest()
    return None


def _git_state() -> dict[str, Any] | None:
    try:
        commit = subprocess.run(
            ["git", "rev-parse", "HEAD"],
            capture_output=True, text=True, timeout=10, check=True,
            cwd=Path(__file__).resolve().parent,
        ).stdout.strip()
        dirty = bool(
            subprocess.run(
                ["git", "status", "--porcelain"],
                capture_output=True, text=True, timeout=10, check=True,
                cwd=Path(__file__).resolve().parent,
            ).stdout.strip()
        )
    except (OSError, subprocess.SubprocessError):
        return None
    return {"commit": commit, "dirty": dirty}


def capture_environment() -> dict[str, Any]:
    """Produce a schema-valid irrevonbench/environment/v1 document."""
    return {
        "format": "irrevonbench/environment/v1",
        "captured_at": datetime.now(UTC).isoformat().replace("+00:00", "Z"),
        "python": {
            "version": platform.python_version(),
            "implementation": platform.python_implementation(),
        },
        "platform": {
            "system": platform.system() or "unknown",
            "release": platform.release() or "unknown",
            "machine": platform.machine() or "unknown",
        },
        "packages": _package_versions(),
        "lockfile_sha256": _lockfile_sha256(),
        "git": _git_state(),
        "container": None,
        "test_hooks_armed": os.environ.get("IRREVON_TEST_HOOKS") == "1",
    }


def python_entrypoint_note() -> str:  # pragma: no cover - debugging affordance
    return sys.executable
