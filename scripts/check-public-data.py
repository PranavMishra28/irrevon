#!/usr/bin/env python3
"""Fail closed on repository-local public-data and media-metadata hazards.

This complements gitleaks and the optional private tripword list. It reports
paths, never matching values.
"""

from __future__ import annotations

import argparse
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
GENERATED_ROOTS = ("site/dist", "dist", "src/irrevon/_web")
# Path-only exceptions for already-reachable synthetic regression/task text.
# Values are intentionally never recorded or printed. New paths always fail.
HISTORY_PATH_ALLOWLIST = {
    "tasks/T-120-reconcile-pr13-and-consolidate-guides.md",
    "tests/cli/test_demo_security.py",
}


def tracked_files() -> list[Path]:
    names = subprocess.check_output(
        ["git", "ls-files", "-z"], cwd=ROOT
    ).split(b"\0")
    return [ROOT / name.decode("utf-8", "surrogateescape") for name in names if name]


def fail(relative: str, reason: str) -> None:
    global failed
    failed = True
    print(f"public-data: {relative}: {reason}", file=sys.stderr)


def inspect_path(path: Path, relative: str) -> None:
    if not path.is_file():
        return
    name = path.name.lower()
    if (name == ".env" or name.startswith(".env.")) and name != ".env.example":
        fail(relative, "tracked/generated environment file")
    data = path.read_bytes()
    inspect_bytes(data, relative)
    suffix = path.suffix.lower()
    if suffix == ".png" and any(chunk in data for chunk in PNG_METADATA_CHUNKS):
        fail(relative, "PNG carries ancillary text or EXIF metadata")
    elif suffix in {".jpg", ".jpeg"} and b"Exif\x00\x00" in data:
        fail(relative, "JPEG carries EXIF metadata")
    elif suffix in {".mp4", ".mov", ".m4v"}:
        fail(relative, "video requires an explicit sanitized-media review")


def inspect_bytes(data: bytes, relative: str, *, history: bool = False) -> None:
    if len(data) > MAX_TEXT:
        return
    reason = None
    if MACHINE_PATH.search(data):
        reason = "contains an absolute user-machine path"
    elif PASSWORD_DSN.search(data) and b"<password>" not in data:
        reason = "contains a password-bearing PostgreSQL DSN"
    if reason and (not history or relative not in HISTORY_PATH_ALLOWLIST):
        fail(relative, f"reachable history {reason}" if history else reason)


def inspect_history() -> int:
    rows = subprocess.check_output(
        ["git", "rev-list", "--objects", "--all"], cwd=ROOT, text=True
    ).splitlines()
    paths_by_object: dict[str, set[str]] = {}
    for row in rows:
        object_id, separator, relative = row.partition(" ")
        if separator and relative:
            paths_by_object.setdefault(object_id, set()).add(relative)

    process = subprocess.Popen(
        ["git", "cat-file", "--batch"],
        cwd=ROOT,
        stdin=subprocess.PIPE,
        stdout=subprocess.PIPE,
    )
    assert process.stdin is not None and process.stdout is not None
    allowed = 0
    for object_id, paths in paths_by_object.items():
        process.stdin.write(f"{object_id}\n".encode())
        process.stdin.flush()
        header = process.stdout.readline().decode("ascii").strip().split()
        if len(header) != 3:
            process.kill()
            raise RuntimeError(f"unexpected git cat-file header for {object_id}")
        _, object_type, raw_size = header
        size = int(raw_size)
        data = process.stdout.read(size)
        if process.stdout.read(1) != b"\n":
            process.kill()
            raise RuntimeError(f"unterminated git cat-file object {object_id}")
        if object_type != "blob" or size > MAX_TEXT:
            continue
        for relative in paths:
            before = failed
            inspect_bytes(data, relative, history=True)
            if not before and relative in HISTORY_PATH_ALLOWLIST and (
                MACHINE_PATH.search(data)
                or (PASSWORD_DSN.search(data) and b"<password>" not in data)
            ):
                allowed += 1
    process.stdin.close()
    if process.wait() != 0:
        raise RuntimeError("git cat-file --batch failed")
    return allowed


parser = argparse.ArgumentParser(description=__doc__)
parser.add_argument(
    "--include-generated",
    action="store_true",
    help="also scan existing release/site/workbench build outputs",
)
args = parser.parse_args()

failed = False
for path in tracked_files():
    relative = path.relative_to(ROOT).as_posix()
    inspect_path(path, relative)

if args.include_generated:
    for root_name in GENERATED_ROOTS:
        generated_root = ROOT / root_name
        if generated_root.is_dir():
            for path in generated_root.rglob("*"):
                inspect_path(path, path.relative_to(ROOT).as_posix())

allowed_history = inspect_history()

if failed:
    raise SystemExit(1)
print(
    "public-data: defined-pattern scan passed for current/generated paths, DSNs, "
    "environment files, media metadata, and reachable history "
    f"({allowed_history} allowlisted historical blobs); "
    "not an exhaustive historical-PII audit"
)
