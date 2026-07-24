"""Regression contract for complete, low-noise Dependabot coverage."""

from __future__ import annotations

import re
from pathlib import Path

ROOT = Path(__file__).parent.parent.parent
CONFIG_PATH = ROOT / ".github/dependabot.yml"
OWNER = "PranavMishra28"


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


def test_every_dependency_tree_has_one_noise_contained_update_lane() -> None:
    blocks = _update_blocks()
    expected_prefixes = {
        ("github-actions", "/"): "ci",
        ("uv", "/"): "deps",
        ("npm", "/web"): "deps",
        ("npm", "/site"): "deps",
        ("docker", "/"): "deps",
    }

    assert set(blocks) == set(expected_prefixes)
    assert (ROOT / "uv.lock").is_file()
    assert (ROOT / "web/pnpm-lock.yaml").is_file()
    assert (ROOT / "site/pnpm-lock.yaml").is_file()

    for key, prefix in expected_prefixes.items():
        block = blocks[key]
        assert 'interval: "monthly"' in block
        assert "default-days: 7" in block
        assert "open-pull-requests-limit: 1" in block
        assert f'- "{OWNER}"' in block
        assert f'prefix: "{prefix}"' in block


def test_site_updates_are_grouped_and_major_migrations_stay_human_reviewed() -> None:
    site = _update_blocks()[("npm", "/site")]

    assert 'update-types: ["version-update:semver-major"]' in site
    assert re.search(
        r"(?m)^      site-minor-patch:\n"
        r'        patterns: \["\*"\]\n'
        r'        update-types: \["minor", "patch"\]$',
        site,
    )
    assert re.search(
        r"(?m)^      site-security:\n"
        r"        applies-to: security-updates\n"
        r'        patterns: \["\*"\]$',
        site,
    )
