#!/usr/bin/env python3
"""Generate THIRD-PARTY-NOTICES.md from scripts/third-party.json (drift-gated).

Design (legal-readiness review §1.6, adapted to this repo's determinism posture):
the committed, reviewable inventory is the registry — scripts/third-party.json —
and the notices file is generated from it. Deviation from the original sketch,
recorded honestly: the original design read INSTALLED metadata (importlib.metadata
+ `pnpm licenses`), which would make `make check` depend on synced virtualenvs and
node_modules; `make check` is deliberately node-free and install-free, so --check
here verifies (a) byte-parity of the generated file against regeneration and
(b) COVERAGE: every direct dependency declared in pyproject.toml,
web/package.json, and site/package.json has an inventory row. A new dependency
therefore fails CI until its license is recorded; recorded license VALUES are
review-verified (same trust model as site/CLAIMS.md).

Usage:
    python3 scripts/build-third-party-notices.py           # regenerate
    python3 scripts/build-third-party-notices.py --check   # CI drift + coverage gate
"""

from __future__ import annotations

import json
import re
import sys
import tomllib
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
REGISTRY = ROOT / "scripts" / "third-party.json"
OUTPUT = ROOT / "THIRD-PARTY-NOTICES.md"

SECTIONS = [
    ("python_runtime", "1. Python wheel/sdist — runtime dependencies",
     "Installed by every user of the packaged artifact; pinned by `uv.lock`."),
    ("web_shipped", "2. Embedded workbench bundle (`web/dist` inside the wheel)",
     "ADR-0018 embeds the built workbench in the wheel and sdist — the wheel is a "
     "redistribution event for these packages; their license-preservation duties "
     "attach to the PyPI artifact, not just the web build."),
    ("fonts", "3. Fonts — IBM Plex Sans / IBM Plex Mono (OFL-1.1)",
     "Full license text: the `OFL.txt` adjacent to the font files "
     "(`web/public/fonts/OFL.txt`, `site/src/assets/fonts/OFL.txt`), copied into "
     "built output with them. Local re-subsetting is prohibited without a registry "
     "+ counsel revisit (would create a Modified Version under the RFN clause)."),
    ("site", "4. Marketing site (`site/dist`)",
     "Static HTML/CSS + self-hosted OFL fonts; never ships in the Python wheel."),
    ("python_dev", "5a. Dev/test dependencies — Python (never distributed)",
     "SBOM-only; no shipped artifact contains them."),
    ("web_dev", "5b. Dev/test dependencies — web (never distributed)",
     "SBOM-only; no shipped artifact contains them."),
]

HEADER = """\
<!-- GENERATED FILE — DO NOT EDIT BY HAND.
     Source: scripts/third-party.json · Generator: scripts/build-third-party-notices.py
     Drift-gated by `make third-party` (part of `make check`). -->

# Third-party notices

## 0. Scope

This inventory covers the third-party components of the Irrevon artifacts: the
Python wheel/sdist (which embeds the built workbench, ADR-0018), the workbench
build (`web/`), the marketing site build (`site/`), and the vendored fonts.
**Status: staged, pre-release.** No Irrevon artifact has been published and the
project's own code and content are licensed under Apache-2.0 (ADR-0028; see
LICENSE, NOTICE, and LICENSING.md). Third-party redistribution obligations remain
separate from that project license and attach when covered artifacts are
redistributed. At first project release this file gains the full license texts
required by the MIT/ISC/BSD notice clauses; until then it is the committed,
drift-gated inventory (the reviewable registry the release-time SBOM is checked
against).

Dev/test dependencies (sections 5a/5b) are never distributed and appear for
SBOM completeness only. MPL-2.0 items (hypothesis, pathspec, @axe-core/playwright)
are dev-only and unmodified: no obligations attach to any shipped artifact.
"""


def render(registry: dict) -> str:
    parts = [HEADER]
    for key, title, blurb in SECTIONS:
        parts.append(f"\n## {title}\n")
        parts.append(f"{blurb}\n")
        parts.append("\n| Component | Version | License | Homepage | Notes |")
        parts.append("\n|---|---|---|---|---|")
        for row in registry[key]:
            home = f"<{row['homepage']}>" if row["homepage"] else "—"
            note = row["note"] or "—"
            parts.append(
                f"\n| `{row['name']}` | {row['version']} | {row['license']} | {home} | {note} |"
            )
        parts.append("\n")
    return "".join(parts)


def normalize(dep: str) -> str:
    """Strip extras and version specifiers from a PEP 508 requirement string."""
    return re.split(r"[\[<>=!~ ]", dep.strip())[0]


def direct_deps() -> dict[str, list[str]]:
    py = tomllib.loads((ROOT / "pyproject.toml").read_text())
    out: dict[str, list[str]] = {}
    out["python (runtime)"] = [normalize(d) for d in py["project"]["dependencies"]]
    out["python (dev group)"] = [
        normalize(d) for d in py.get("dependency-groups", {}).get("dev", [])
    ]
    for pkg in ("web", "site"):
        data = json.loads((ROOT / pkg / "package.json").read_text())
        out[f"{pkg} (deps)"] = sorted(data.get("dependencies", {}))
        out[f"{pkg} (devDeps)"] = sorted(data.get("devDependencies", {}))
    return out


def covered_names(registry: dict) -> str:
    """One searchable haystack of every registry row's name + note text."""
    chunks = []
    for rows in registry.values():
        if not isinstance(rows, list):
            continue
        for row in rows:
            chunks.append(row["name"])
            chunks.append(row.get("note", ""))
    return "\n".join(chunks)


# psycopg[binary] is one requirement covering two rows; extras normalize to the base.
ALIASES = {"psycopg": "psycopg"}


def check_coverage(registry: dict) -> list[str]:
    haystack = covered_names(registry)
    missing = []
    for group, names in direct_deps().items():
        for name in names:
            # A dep is covered if its (aliased) name appears anywhere in a row
            # name or note — rows may aggregate (e.g. "react / react-dom").
            probe = ALIASES.get(name, name)
            if probe not in haystack:
                missing.append(f"{group}: {name}")
    return missing


def main() -> int:
    registry = json.loads(REGISTRY.read_text())
    rendered = render(registry)
    if "--check" in sys.argv:
        fail = False
        if not OUTPUT.exists() or OUTPUT.read_text() != rendered:
            print("third-party: DRIFT — THIRD-PARTY-NOTICES.md does not match the registry;")
            print("  run: python3 scripts/build-third-party-notices.py")
            fail = True
        missing = check_coverage(registry)
        if missing:
            print("third-party: COVERAGE FAIL — direct dependencies without an inventory row:")
            for m in missing:
                print(f"  {m}")
            print("  add a row (with its verified license) to scripts/third-party.json")
            fail = True
        if fail:
            return 1
        print("third-party: notices in sync; every direct dependency covered")
        return 0
    OUTPUT.write_text(rendered)
    print(f"third-party: wrote {OUTPUT.relative_to(ROOT)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
