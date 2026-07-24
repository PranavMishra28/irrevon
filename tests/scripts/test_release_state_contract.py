"""Contract tests for the candidate-to-published release-state transition."""

from __future__ import annotations

import json
import re
from copy import deepcopy
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
STATUS_PATH = ROOT / "docs" / "project-status.json"
TRUTH_GATE = ROOT / "scripts" / "check-public-truth.py"
SITE_PROVENANCE = ROOT / "site" / "src" / "lib" / "release-provenance.ts"


def _valid(release: dict[str, object]) -> bool:
    if release.get("state") not in {"candidate", "published"}:
        return False
    version = release.get("version")
    if version != "0.1.0" or release.get("tag") != f"v{version}":
        return False
    if release.get("package") != "irrevon" or release.get("channel") != "alpha":
        return False
    if release.get("pypi_url") != f"https://pypi.org/project/irrevon/{version}/":
        return False
    if release.get("github_release_url") != (
        f"https://github.com/PranavMishra28/irrevon/releases/tag/v{version}"
    ):
        return False
    published_at = release.get("published_at")
    commit_sha = release.get("commit_sha")
    if release["state"] == "candidate":
        return published_at is None and commit_sha is None
    return (
        isinstance(published_at, str)
        and re.fullmatch(r"\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}Z", published_at) is not None
        and isinstance(commit_sha, str)
        and re.fullmatch(r"[0-9a-f]{40}", commit_sha) is not None
    )


def test_committed_candidate_has_no_publication_evidence() -> None:
    release = json.loads(STATUS_PATH.read_text())["software_release"]
    assert release["state"] == "candidate"
    assert _valid(release)
    assert release["published_at"] is None
    assert release["commit_sha"] is None


def test_published_transition_requires_complete_external_evidence() -> None:
    candidate = json.loads(STATUS_PATH.read_text())["software_release"]

    incomplete = deepcopy(candidate)
    incomplete["state"] = "published"
    assert not _valid(incomplete)

    complete = deepcopy(incomplete)
    complete["published_at"] = "2026-07-24T20:15:00Z"
    complete["commit_sha"] = "a" * 40
    assert _valid(complete)

    dishonest_candidate = deepcopy(candidate)
    dishonest_candidate["commit_sha"] = "a" * 40
    assert not _valid(dishonest_candidate)


def test_every_release_consumer_uses_the_single_status_object() -> None:
    truth = TRUTH_GATE.read_text()
    site = SITE_PROVENANCE.read_text()
    for consumer in (truth, site):
        assert "software_release" in consumer
        assert "published_at" in consumer
        assert "commit_sha" in consumer
    for retired_key in ("release_posture", "prepared_version", "prepared_label"):
        assert retired_key not in truth
        assert retired_key not in site
