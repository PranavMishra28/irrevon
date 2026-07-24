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
    ".github/nightly-failure-body.md",
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
    "v0.1.0` alpha candidate",
    "make web-build dist-stage",
    "--dsn postgresql://irrevon_app@localhost:5432/irrevon_demo_s42",
    "--demo-artifact ./irrevon-demo-artifact.json",
):
    if expected not in readme:
        fail(f"README.md is missing status marker {expected!r}")

if STATUS["license"] != "Apache-2.0":
    fail("project-status.json license must remain Apache-2.0")
if STATUS["release_posture"] != "research-preview-unpublished":
    fail("project-status.json must preserve unpublished research-preview posture")
if STATUS.get("prepared_label") != "v0.1.0-alpha-candidate":
    fail("project-status.json must label the prepared version as an alpha candidate")
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
expected_site = {
    "alias": "https://irrevon.vercel.app/",
    "state": "stale-pre-main-build",
    "observed_content": "matches-2026-07-22-pre-main-build",
    "version_json": "absent",
    "deployed_commit_proof": False,
}
if STATUS["deployment"].get("public_site") != expected_site:
    fail("project-status.json must preserve the exact stale public-site read-back")
if any(
    value != "draft-never-live-called"
    for value in STATUS["provider_adapters"].values()
    if isinstance(value, str)
):
    fail("provider adapters must remain draft-never-live-called")
if STATUS.get("public_history_privacy") != {
    "status": "known-history-only-exposure",
    "automated_rewrite_allowed": False,
    "owner_decision": "accept-exposure-or-coordinate-history-rewrite",
}:
    fail("project-status.json must preserve the owner accept-or-rewrite history blocker")

settings = STATUS.get("owner_settings_readback", {})
for key in (
    "discussions",
    "non_provider_secret_scanning",
    "immutable_releases",
    "actions_allowlist",
    "actions_sha_pinning_enforcement",
    "release_environment",
    "sandbox_environment",
    "benchmark_environment",
):
    if settings.get(key) is not False:
        fail(f"project-status.json owner read-back must keep {key!r} false")
if settings.get("ruleset") != "active-with-repository-role-bypass":
    fail("project-status.json must preserve the active ruleset bypass blocker")

discussion_surfaces = (
    "README.md",
    "SUPPORT.md",
    "CONTRIBUTING.md",
    "CODE_OF_CONDUCT.md",
    ".github/ISSUE_TEMPLATE/config.yml",
    "docs/project-status.md",
    "docs/security-policy.md",
    "docs/ci.md",
    "docs/discoverability.md",
)
for relative in discussion_surfaces:
    body = (ROOT / relative).read_text(encoding="utf-8")
    if "github.com/PranavMishra28/irrevon/discussions" in body:
        fail(f"{relative} exposes a Discussion URL while Discussions is disabled")

expected_discussions = {
    "enabled": False,
    "public_links_exposed": False,
    "intended_categories": [
        "Announcements",
        "Q&A",
        "Ideas and feedback",
        "Show and tell",
    ],
    "owner_gate": [
        "enable-discussions",
        "create-or-verify-categories",
        "publish-and-pin-welcome-post",
        "read-back-every-category-url",
    ],
}
if STATUS.get("community", {}).get("discussions") != expected_discussions:
    fail("project-status.json must preserve the disabled Discussions owner gate")

for relative in (
    "README.md",
    "SUPPORT.md",
    "CONTRIBUTING.md",
    "docs/project-status.md",
    "docs/security-policy.md",
    "docs/ci.md",
    "docs/discoverability.md",
):
    body = (ROOT / relative).read_text(encoding="utf-8")
    normalized = " ".join(line.removeprefix("> ").strip() for line in body.splitlines())
    for marker in (
        "Announcements",
        "Q&A",
        "Ideas and feedback",
        "Show and tell",
        "pin a welcome post",
        "read back every category URL",
    ):
        if marker not in normalized:
            fail(f"{relative} is missing Discussions owner-gate marker {marker!r}")

advisory_url = "https://github.com/PranavMishra28/irrevon/security/advisories/new"
for relative in ("README.md", "SUPPORT.md", "CONTRIBUTING.md", ".github/ISSUE_TEMPLATE/config.yml"):
    if advisory_url not in (ROOT / relative).read_text(encoding="utf-8"):
        fail(f"{relative} must link private vulnerability reporting")

public_templates = {
    path.name for path in (ROOT / ".github/ISSUE_TEMPLATE").iterdir() if path.is_file()
}
if "nightly-failure.md" in public_templates:
    fail("internal nightly failure body must not appear in the public issue chooser")
if "question.yml" in public_templates:
    fail("usage questions must not become an issue route while public Q&A is unavailable")
nightly_workflow = (ROOT / ".github/workflows/nightly.yml").read_text(encoding="utf-8")
if ".github/nightly-failure-body.md" not in nightly_workflow:
    fail("nightly workflow must consume the internal failure body")

operations = (ROOT / "docs/operations.md").read_text(encoding="utf-8")
for expected in (
    "uv run python -m irrevon.adapters.refdest_server",
    "uv run irrevon worker",
    "--health-file .scratch/worker-health.json",
    "--max-cycles 3",
    "not production evidence",
):
    if expected not in operations:
        fail(f"docs/operations.md is missing synthetic worker marker {expected!r}")

citation = (ROOT / "CITATION.cff").read_text(encoding="utf-8")
for expected in (
    'repository-code: "https://github.com/PranavMishra28/irrevon"',
    'license: "Apache-2.0"',
    f'version: "{STATUS["prepared_version"]}"',
    "confirmatory benchmark result or package-index release exists yet.",
    "exact version or commit",
):
    if expected not in citation:
        fail(f"CITATION.cff is missing truthful citation marker {expected!r}")
if STATUS["release_posture"] == "research-preview-unpublished":
    if "\ndate-released:" in citation:
        fail("CITATION.cff must not assign a release date before publication")

package_init = (ROOT / "src/irrevon/__init__.py").read_text(encoding="utf-8")
version_match = re.search(r'^__version__ = "([^"]+)"$', package_init, flags=re.MULTILINE)
if not version_match or version_match.group(1) != STATUS["prepared_version"]:
    fail("package version must exactly match project-status.json prepared_version")

codeowners_lines = [
    line.split()
    for line in (ROOT / ".github/CODEOWNERS").read_text(encoding="utf-8").splitlines()
    if line.strip() and not line.lstrip().startswith("#")
]
if not codeowners_lines or codeowners_lines[0] != ["*", "@PranavMishra28"]:
    fail("CODEOWNERS must begin with the repository-wide '* @PranavMishra28' rule")
for rule in codeowners_lines:
    if len(rule) < 2 or "@PranavMishra28" not in rule[1:]:
        fail(f"CODEOWNERS rule {rule[0]!r} must retain the repository owner")
if not any(rule[0] in {"*", "/.github/", ".github/"} for rule in codeowners_lines):
    fail("CODEOWNERS must own .github/CODEOWNERS itself")

schema_count = len(list((ROOT / "schemas").glob("*.schema.json")))
if schema_count != 13:
    fail(f"schema inventory expected 13, found {schema_count}")

if failed:
    raise SystemExit(1)
print("public-truth: launch status, community posture, and 13-schema inventory agree")
