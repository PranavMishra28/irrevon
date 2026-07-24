"""Fail-closed contract for release-state-driven public changelog truth."""

from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
PAGE = ROOT / "site" / "src" / "pages" / "changelog.astro"


def test_changelog_uses_verified_release_state_not_checkout_tags() -> None:
    page = PAGE.read_text()
    assert 'RELEASE_STATE === "published"' in page
    assert "PYPI_PROJECT_URL" in page
    assert "GITHUB_RELEASE_URL" in page
    assert "RELEASE_COMMIT" in page
    assert "git tag --list" not in page
    assert "No releases yet" not in page
    assert "Package release in progress" in page
