#!/usr/bin/env python3
"""Generate the root ASSETS.md from scripts/assets-registry.json (drift-gated).

Design (legal-readiness review §2): one committed registry at repo root, generated
from a machine-readable source with a --check drift gate — exactly the
site/CLAIMS.md pattern. The --check mode additionally does a COVERAGE SWEEP:
every binary/vector asset under web/public/, site/public/, site/src/assets/, and
site/og/ must belong to a registry row, and every row path must exist with a
matching sha256 — an unregistered, missing, or drifted asset fails CI. Rationale:
working provenance histories are local-only (gitignored); this registry moves the
load-bearing provenance statements into the committed public tree.

Usage:
    python3 scripts/build-assets-registry.py           # regenerate (refreshes sha256)
    python3 scripts/build-assets-registry.py --check   # CI drift + coverage gate
"""

from __future__ import annotations

import hashlib
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
REGISTRY = ROOT / "scripts" / "assets-registry.json"
OUTPUT = ROOT / "ASSETS.md"

SWEEP_DIRS = ["web/public", "site/public", "site/src/assets", "site/og"]
SWEEP_EXTS = {".svg", ".png", ".woff2", ".txt", ".ico", ".jpg", ".jpeg", ".webp", ".gif"}
# Generated manifest JSON files are data, not assets; the site og/manifest.json
# is drift-gated by its own script.
SWEEP_EXCLUDE = {"site/og/manifest.json"}

HEADER = """\
<!-- GENERATED FILE — DO NOT EDIT BY HAND.
     Source: scripts/assets-registry.json · Generator: scripts/build-assets-registry.py
     Drift-gated by `make assets` (part of `make check`): byte-parity, per-file
     sha256 match, and a coverage sweep over web/public/, site/public/,
     site/src/assets/, site/og/. -->

# ASSETS.md — asset provenance registry

Every committed binary/vector asset is recorded here with origin, license, and a
provenance statement; file hashes are drift-gated. Policy: original, hand-written
geometry only; references may be studied for direction and must be named; no
traced, copied, or auto-generated third-party geometry; no stock, no clip-art, no
AI-image imports. Fonts are the repository's licensed set only.

The repository currently carries no license (LICENSING.md; ADR-0014 open):
project-original assets are recorded for future licensing decisions; nothing here
grants or implies external reuse rights. `site/ASSETS.md` is a pointer to this
registry.
"""


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def render(registry: dict) -> str:
    parts = [HEADER]
    parts.append(f"\n## Reference imagery (preamble)\n\n{registry['preamble']}\n")
    for i, row in enumerate(registry["rows"], 1):
        parts.append(f"\n## {i}. {row['asset']}\n\n")
        parts.append(f"- **type:** {row['type']} · **origin:** {row['origin']} · ")
        parts.append(f"**license:** {row['license']} · **date:** {row['date']}\n")
        parts.append(f"- **source:** {row['source']}\n")
        parts.append(f"- **provenance:** {row['provenance']}\n")
        parts.append("- **files (sha256):**\n")
        for p in row["paths"]:
            f = ROOT / p
            digest = sha256(f) if f.exists() else "MISSING"
            parts.append(f"  - `{p}` — `{digest}`\n")
    return "".join(parts)


def sweep() -> list[str]:
    found = []
    for d in SWEEP_DIRS:
        base = ROOT / d
        if not base.exists():
            continue
        for f in sorted(base.rglob("*")):
            rel = f.relative_to(ROOT).as_posix()
            if f.is_file() and f.suffix.lower() in SWEEP_EXTS and rel not in SWEEP_EXCLUDE:
                found.append(rel)
    return found


def main() -> int:
    registry = json.loads(REGISTRY.read_text())
    registered = {p for row in registry["rows"] for p in row["paths"]}
    rendered = render(registry)

    if "--check" in sys.argv:
        fail = False
        if not OUTPUT.exists() or OUTPUT.read_text() != rendered:
            print("assets: DRIFT — ASSETS.md does not match the registry (or a file hash");
            print("  changed); run: python3 scripts/build-assets-registry.py")
            fail = True
        missing = [p for p in registered if not (ROOT / p).exists()]
        if missing:
            print("assets: FAIL — registry rows point at missing files:")
            for p in missing:
                print(f"  {p}")
            fail = True
        unregistered = [p for p in sweep() if p not in registered]
        if unregistered:
            print("assets: COVERAGE FAIL — committed assets without a registry row:")
            for p in unregistered:
                print(f"  {p}")
            print("  add a row to scripts/assets-registry.json (provenance required)")
            fail = True
        if fail:
            return 1
        print("assets: registry in sync; every swept asset registered")
        return 0

    OUTPUT.write_text(rendered)
    print(f"assets: wrote {OUTPUT.relative_to(ROOT)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
