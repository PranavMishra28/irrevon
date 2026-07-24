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
    "single-writer",
    "v0.1.0",
    "Alpha",
    "make web-build dist-stage",
    "--dsn postgresql://irrevon_app@localhost:5432/irrevon_demo_s42",
    "--demo-artifact ./irrevon-demo-artifact.json",
):
    if expected not in readme:
        fail(f"README.md is missing status marker {expected!r}")

if STATUS["license"] != "Apache-2.0":
    fail("project-status.json license must remain Apache-2.0")
release = STATUS.get("software_release")
if not isinstance(release, dict):
    fail("project-status.json software_release must be an object")
    release = {}
release_state = release.get("state")
release_version = release.get("version")
expected_release = {
    "package": "irrevon",
    "version": "0.1.0",
    "tag": "v0.1.0",
    "channel": "alpha",
    "pypi_url": "https://pypi.org/project/irrevon/0.1.0/",
    "github_release_url": "https://github.com/PranavMishra28/irrevon/releases/tag/v0.1.0",
}
for key, expected in expected_release.items():
    if release.get(key) != expected:
        fail(f"project-status.json software_release.{key} must be {expected!r}")
if release_state not in {"candidate", "published"}:
    fail("project-status.json software_release.state must be candidate or published")
published_at = release.get("published_at")
release_commit = release.get("commit_sha")
if release_state == "candidate":
    if published_at is not None or release_commit is not None:
        fail("candidate release cannot carry publication timestamp or commit evidence")
elif release_state == "published":
    if not isinstance(published_at, str) or not re.fullmatch(
        r"\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}Z", published_at
    ):
        fail("published release requires an RFC 3339 UTC publication timestamp")
    if not isinstance(release_commit, str) or not re.fullmatch(r"[0-9a-f]{40}", release_commit):
        fail("published release requires the exact 40-character release commit")
    for marker in (
        f"irrevon=={release_version}",
        str(release["pypi_url"]),
        str(release["github_release_url"]),
    ):
        if marker not in readme:
            fail(f"README.md is missing published release marker {marker!r}")
    for obsolete in ("release-unpublished", "not published", "alpha candidate"):
        if obsolete in readme.lower():
            fail(f"README.md retains obsolete published-state marker {obsolete!r}")
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
    "state": "ready-current",
    "deployment_mode": "main-auto-deploy",
    "observed_content": "matches-current-main",
    "version_json": "present",
    "deployed_commit_proof": True,
}
if STATUS["deployment"].get("public_site") != expected_site:
    fail("project-status.json must preserve the verified current public-site read-back")
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
    "immutable_releases",
    "actions_allowlist",
    "actions_sha_pinning_enforcement",
    "release_environment",
):
    if settings.get(key) is not True:
        fail(f"project-status.json owner read-back must keep {key!r} true")
for key in (
    "non_provider_secret_scanning",
    "sandbox_environment",
    "benchmark_environment",
):
    if settings.get(key) is not False:
        fail(f"project-status.json owner read-back must keep {key!r} false")
discussions = STATUS.get("community", {}).get("discussions", {})
if settings.get("discussions") is not discussions.get("enabled"):
    fail("project-status.json Discussions setting and community read-back disagree")
if settings.get("ruleset") != "active-no-bypass-actors":
    fail("project-status.json must preserve the active ruleset with no bypass actors")

discussion_surfaces = (
    "README.md",
    "SUPPORT.md",
    "CONTRIBUTING.md",
    ".github/ISSUE_TEMPLATE/config.yml",
)
discussion_url = "https://github.com/PranavMishra28/irrevon/discussions"
if discussions.get("enabled") is True:
    if discussions.get("url") != discussion_url:
        fail("project-status.json must record the canonical Discussions URL")
    if discussions.get("public_links_exposed") is not True:
        fail("enabled Discussions must be exposed on public community surfaces")
    expected_categories = {
        name: f"{discussion_url}/categories/{slug}"
        for name, slug in (
            ("Announcements", "announcements"),
            ("General", "general"),
            ("Ideas", "ideas"),
            ("Polls", "polls"),
            ("Q&A", "q-a"),
            ("Show and tell", "show-and-tell"),
        )
    }
    categories = discussions.get("categories")
    if (
        not isinstance(categories, list)
        or {item.get("name"): item.get("url") for item in categories if isinstance(item, dict)}
        != expected_categories
    ):
        fail("project-status.json Discussion categories differ from the verified defaults")
    welcome_url = discussions.get("welcome_url")
    if welcome_url is not None and (
        not isinstance(welcome_url, str) or not welcome_url.startswith(f"{discussion_url}/")
    ):
        fail("project-status.json welcome Discussion URL is not canonical")
    expected_category_urls = set(expected_categories.values())
    for relative in discussion_surfaces:
        body = (ROOT / relative).read_text(encoding="utf-8")
        if discussion_url not in body:
            fail(f"{relative} must expose the verified Discussions URL")
        exposed_categories = set(
            re.findall(
                rf"{re.escape(discussion_url)}/categories/[a-z0-9-]+",
                body,
            )
        )
        unexpected_categories = exposed_categories - expected_category_urls
        if unexpected_categories:
            fail(
                f"{relative} exposes unverified Discussion categories "
                f"{sorted(unexpected_categories)!r}"
            )
elif discussions.get("enabled") is False:
    if discussions.get("public_links_exposed") is not False:
        fail("disabled Discussions cannot be marked as publicly exposed")
    for relative in discussion_surfaces:
        if discussion_url in (ROOT / relative).read_text(encoding="utf-8"):
            fail(f"{relative} exposes a Discussion URL while Discussions is disabled")
else:
    fail("project-status.json community.discussions.enabled must be boolean")

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
    f'version: "{release_version}"',
    "confirmatory benchmark result",
    "exact version or commit",
):
    if expected not in citation:
        fail(f"CITATION.cff is missing truthful citation marker {expected!r}")
if release_state == "candidate":
    if "\ndate-released:" in citation:
        fail("CITATION.cff must not assign a release date before publication")
elif release_state == "published":
    if f"\ndate-released: {str(published_at)[:10]}" not in citation:
        fail("CITATION.cff release date must match verified publication evidence")
    if "package-index release exists yet" in citation:
        fail("CITATION.cff retains an obsolete unpublished-package claim")

package_init = (ROOT / "src/irrevon/__init__.py").read_text(encoding="utf-8")
version_match = re.search(r'^__version__ = "([^"]+)"$', package_init, flags=re.MULTILINE)
if not version_match or version_match.group(1) != release_version:
    fail("package version must exactly match project-status.json software_release.version")

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
