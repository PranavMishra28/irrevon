"""Fail-closed contract for the release-only generated changelog."""

from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
PAGE = ROOT / "site" / "src" / "pages" / "changelog.astro"


def test_changelog_filters_for_annotated_semver_release_tags() -> None:
    page = PAGE.read_text()
    assert "%(objecttype)" in page
    assert 'objectType === "tag"' in page
    assert (
        r"/^v(0|[1-9][0-9]*)\.(0|[1-9][0-9]*)\.(0|[1-9][0-9]*)$/.test(tag)"
        in page
    )
    assert "signed tag" not in page.lower()
    assert "0 releases" in page
