"""Regression contract for consolidated routine and prompt security updates."""

from __future__ import annotations

import re
from pathlib import Path

ROOT = Path(__file__).parent.parent.parent
CONFIG_PATH = ROOT / ".github/dependabot.yml"
OWNER = "PranavMishra28"
ROUTINE_GROUP = "monthly-routine"


def _update_blocks() -> dict[tuple[str, str], str]:
    config = CONFIG_PATH.read_text()
    raw_blocks = re.findall(
        r"(?ms)^  - package-ecosystem:.*?(?=^  - package-ecosystem:|\Z)",
        config,
    )
    blocks: dict[tuple[str, str], str] = {}
    for block in raw_blocks:
        ecosystem = re.search(r'^  - package-ecosystem: "([^"]+)"$', block, re.MULTILINE)
        directory = re.search(r'^    directory: "([^"]+)"$', block, re.MULTILINE)
        assert ecosystem is not None
        assert directory is not None
        key = (ecosystem.group(1), directory.group(1))
        assert key not in blocks
        blocks[key] = block
    return blocks


def test_every_dependency_tree_joins_the_one_monthly_routine_group() -> None:
    config = CONFIG_PATH.read_text()
    blocks = _update_blocks()
    expected = {
        ("github-actions", "/"),
        ("uv", "/"),
        ("npm", "/web"),
        ("npm", "/site"),
        ("docker", "/"),
    }

    assert set(blocks) == expected
    assert (ROOT / "uv.lock").is_file()
    assert (ROOT / "web/pnpm-lock.yaml").is_file()
    assert (ROOT / "site/pnpm-lock.yaml").is_file()

    group = config.split("multi-ecosystem-groups:\n", 1)[1].split("\nupdates:\n", 1)[0]
    assert re.search(
        rf"(?m)^  {ROUTINE_GROUP}:\n"
        r"    schedule:\n"
        r'      interval: "monthly"$',
        group,
    )
    assert f'- "{OWNER}"' in group
    assert '- "dependencies"' in group
    assert re.search(r'(?m)^    commit-message:\n      prefix: "deps"$', group)

    for key in expected:
        block = blocks[key]
        assert 'patterns: ["*"]' in block
        assert f'multi-ecosystem-group: "{ROUTINE_GROUP}"' in block
        assert "default-days: 7" in block
        assert "open-pull-requests-limit: 1" in block
        assert f'- "{OWNER}"' in block
        assert '- "dependencies"' in block
        assert "commit-message:" not in block
        assert "applies-to: security-updates" in block

    assert not re.search(r"(?m)^\s*(?:auto-merge|automerge):", config)


def test_security_updates_stay_grouped_per_ecosystem() -> None:
    blocks = _update_blocks()
    names = {
        ("github-actions", "/"): "actions-security",
        ("uv", "/"): "python-security",
        ("npm", "/web"): "web-security",
        ("npm", "/site"): "site-security",
        ("docker", "/"): "containers-security",
    }

    for key, name in names.items():
        block = blocks[key]
        assert re.search(
            rf"(?m)^      {name}:\n"
            r"        applies-to: security-updates\n"
            r'        patterns: \["\*"\]$',
            block,
        )


def test_frontend_routine_majors_stay_human_reviewed() -> None:
    blocks = _update_blocks()
    for key in (("npm", "/web"), ("npm", "/site")):
        assert 'update-types: ["version-update:semver-major"]' in blocks[key]

    for key in (("github-actions", "/"), ("uv", "/"), ("docker", "/")):
        assert 'update-types: ["version-update:semver-major"]' not in blocks[key]


def test_quarterly_major_review_is_documented() -> None:
    ci = (ROOT / "docs/ci.md").read_text()
    assert "Quarterly major-upgrade review" in ci
    assert "`/web` and `/site`" in ci
