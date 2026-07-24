#!/usr/bin/env python3
"""Generate exact license texts for every bundled Workbench production package."""

from __future__ import annotations

import argparse
import hashlib
import json
import subprocess
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
OUTPUT = ROOT / "THIRD-PARTY-LICENSES.md"


def production_packages() -> dict[tuple[str, str], Path]:
    raw = subprocess.check_output(
        ["pnpm", "list", "--prod", "--depth", "Infinity", "--json"],
        cwd=ROOT / "web",
        text=True,
    )
    graph = json.loads(raw)[0]
    packages: dict[tuple[str, str], Path] = {}

    def walk(dependencies: dict[str, Any]) -> None:
        for name, entry in dependencies.items():
            if not isinstance(entry, dict):
                continue
            version, package_path = entry.get("version"), entry.get("path")
            if isinstance(version, str) and isinstance(package_path, str):
                packages[(name, version)] = Path(package_path)
            child = entry.get("dependencies")
            if isinstance(child, dict):
                walk(child)

    walk(graph.get("dependencies", {}))
    if not packages:
        raise RuntimeError("pnpm production graph produced no packages")
    return packages


def render() -> str:
    sections = [
        "# Bundled third-party license texts\n\n"
        "Generated from the exact `web/pnpm-lock.yaml` production graph by "
        "`scripts/build-third-party-license-pack.py`. These are the upstream "
        "license files for code bundled into Irrevon's packaged Workbench. "
        "Python dependencies are installed separately and carry their own "
        "distribution metadata.\n"
    ]
    for (name, version), package_path in sorted(production_packages().items()):
        candidates = sorted(
            path
            for path in package_path.iterdir()
            if path.is_file()
            and path.name.lower().startswith(("license", "licence", "copying"))
        )
        if not candidates:
            raise RuntimeError(f"{name}@{version} has no upstream license file")
        license_path = candidates[0]
        text = license_path.read_text(encoding="utf-8").strip()
        license_hash = hashlib.sha256(text.encode()).hexdigest()
        sections.append(
            f"\n\n## {name} {version}\n\n"
            f"Upstream file: `{license_path.name}` · SHA-256 `{license_hash}`\n\n"
            f"```text\n{text}\n```\n"
        )
    return "".join(sections)


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--check", action="store_true")
    args = parser.parse_args()
    rendered = render()
    if args.check:
        if not OUTPUT.is_file() or OUTPUT.read_text(encoding="utf-8") != rendered:
            print("third-party-licenses: drift; regenerate the license pack")
            return 1
        print("third-party-licenses: exact bundled license texts match")
        return 0
    OUTPUT.write_text(rendered, encoding="utf-8")
    print(f"third-party-licenses: wrote {OUTPUT.relative_to(ROOT)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
