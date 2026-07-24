#!/usr/bin/env python3
"""Deterministic launch-facing truth and community consistency gate."""

from __future__ import annotations

import json
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
STATUS = json.loads((ROOT / "docs/project-status.json").read_text())

REQUIRED_FILES = (
    "CHANGELOG.md",
    "CITATION.cff",
    "CODE_OF_CONDUCT.md",
    "CONTRIBUTING.md",
    "DCO",
    "GOVERNANCE.md",
    "LICENSE",
    "LICENSING.md",
    "MAINTAINERS.md",
    "NOTICE",
    "README.md",
    "SECURITY.md",
    "SUPPORT.md",
    ".github/CODEOWNERS",
    ".github/PULL_REQUEST_TEMPLATE.md",
    ".github/ISSUE_TEMPLATE/config.yml",
    "docs/project-status.md",
    "docs/release-process.md",
)

LAUNCH_SURFACES = (
    "README.md",
    "AGENTS.md",
    "CONTRIBUTING.md",
    "LICENSING.md",
    "docs/execution-plan.md",
    "docs/project-status.md",
    "site/src/layouts/Base.astro",
    "site/src/content/guides/getting-started.md",
    "site/src/pages/install.astro",
)

BANNED = {
    r"<repository-url>": "placeholder clone URL",
    r"Contributions are not yet accepted": "obsolete closed-contribution statement",
    r"Do not open PRs yet": "obsolete closed-contribution instruction",
    r"\bpreregistered benchmark\b": "false frozen/preregistered status",
}


def fail(message: str) -> None:
    print(f"public-truth: {message}", file=sys.stderr)
    global failed
    failed = True


failed = False
for relative in REQUIRED_FILES:
    if not (ROOT / relative).is_file():
        fail(f"missing required launch file: {relative}")

texts: dict[str, str] = {}
for relative in LAUNCH_SURFACES:
    path = ROOT / relative
    if not path.is_file():
        fail(f"missing launch surface: {relative}")
        continue
    texts[relative] = path.read_text(encoding="utf-8")

for relative, body in texts.items():
    for pattern, label in BANNED.items():
        if re.search(pattern, body, flags=re.IGNORECASE):
            fail(f"{relative}: {label}")

readme = texts.get("README.md", "")
for expected in (
    "https://github.com/PranavMishra28/irrevon.git",
    "Apache-2.0",
    "DCO",
    "synthetic",
    "never been live-called",
    "single-writer",
    "not yet a supported production",
):
    if expected not in readme:
        fail(f"README.md is missing status marker {expected!r}")

if STATUS["license"] != "Apache-2.0":
    fail("project-status.json license must remain Apache-2.0")
if STATUS["release_posture"] != "research-preview-unpublished":
    fail("project-status.json must preserve unpublished research-preview posture")
if STATUS["contributions"] != {
    "open": True,
    "license": "Apache-2.0",
    "dco": "1.1-required-every-commit",
    "cla": False,
}:
    fail("project-status.json contribution posture drifted")
if STATUS["evidence"]["confirmatory_results"] is not False:
    fail("confirmatory results cannot be claimed")
if STATUS["deployment"]["active_writers"] != 1:
    fail("the evaluated boundary must remain single-writer")
if STATUS["deployment"]["supported_production_topology"] is not False:
    fail("a supported production topology cannot be claimed before its open gates close")
if any(value != "draft-never-live-called" for value in STATUS["provider_adapters"].values()
       if isinstance(value, str)):
    fail("provider adapters must remain draft-never-live-called")

citation = (ROOT / "CITATION.cff").read_text(encoding="utf-8")
for expected in (
    'repository-code: "https://github.com/PranavMishra28/irrevon"',
    'license: "Apache-2.0"',
    "confirmatory benchmark result or package-index release exists yet.",
    "exact version or commit",
):
    if expected not in citation:
        fail(f"CITATION.cff is missing truthful citation marker {expected!r}")
if STATUS["release_posture"] == "research-preview-unpublished":
    for forbidden in ("\nversion:", "\ndate-released:"):
        if forbidden in citation:
            fail(f"CITATION.cff must not imply an unpublished release with {forbidden.strip()!r}")

schema_count = len(list((ROOT / "schemas").glob("*.schema.json")))
if schema_count != 13:
    fail(f"schema inventory expected 13, found {schema_count}")

if failed:
    raise SystemExit(1)
print("public-truth: launch status, community posture, and 13-schema inventory agree")
