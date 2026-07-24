#!/usr/bin/env python3
"""Fail closed on repository-local public-data and media-metadata hazards.

This complements gitleaks and the optional private tripword list. It reports
paths, never matching values.
"""

from __future__ import annotations

import re
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
MAX_TEXT = 4 * 1024 * 1024
MACHINE_PATH = re.compile(
    rb"(?:/Users/[A-Za-z0-9._-]+/|/home/[A-Za-z0-9._-]+/|[A-Za-z]:\\Users\\[^\\]+\\)"
)
PASSWORD_DSN = re.compile(rb"postgres(?:ql)?://[^/\s:@]+:[^@\s/]+@", re.IGNORECASE)
PNG_METADATA_CHUNKS = (b"tEXt", b"zTXt", b"iTXt", b"eXIf")


def tracked_files() -> list[Path]:
    names = subprocess.check_output(
        ["git", "ls-files", "-z"], cwd=ROOT
    ).split(b"\0")
    return [ROOT / name.decode("utf-8", "surrogateescape") for name in names if name]


def fail(relative: str, reason: str) -> None:
    global failed
    failed = True
    print(f"public-data: {relative}: {reason}", file=sys.stderr)


failed = False
for path in tracked_files():
    relative = path.relative_to(ROOT).as_posix()
    if not path.is_file():
        continue
    name = path.name.lower()
    if (name == ".env" or name.startswith(".env.")) and name != ".env.example":
        fail(relative, "tracked environment file")
    data = path.read_bytes()
    if len(data) <= MAX_TEXT:
        if MACHINE_PATH.search(data):
            fail(relative, "contains an absolute user-machine path")
        if PASSWORD_DSN.search(data) and b"<password>" not in data:
            fail(relative, "contains a password-bearing PostgreSQL DSN")
    suffix = path.suffix.lower()
    if suffix == ".png" and any(chunk in data for chunk in PNG_METADATA_CHUNKS):
        fail(relative, "PNG carries ancillary text or EXIF metadata")
    elif suffix in {".jpg", ".jpeg"} and b"Exif\x00\x00" in data:
        fail(relative, "JPEG carries EXIF metadata")
    elif suffix in {".mp4", ".mov", ".m4v"}:
        fail(relative, "tracked video requires an explicit sanitized-media review")

if failed:
    raise SystemExit(1)
print("public-data: tracked paths, DSNs, environment files, and media metadata clean")
