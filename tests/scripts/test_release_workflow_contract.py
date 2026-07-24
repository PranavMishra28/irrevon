"""Fail-closed contract for the executable, owner-gated release workflow."""

from __future__ import annotations

import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
WORKFLOW = ROOT / ".github" / "workflows" / "release.yml"
MAKEFILE = ROOT / "Makefile"


def _job(workflow: str, name: str, next_name: str | None = None) -> str:
    boundary = rf"(?=^  {re.escape(next_name)}:\n)" if next_name else r"\Z"
    match = re.search(
        rf"^  {re.escape(name)}:\n(?P<body>.*?){boundary}",
        workflow,
        flags=re.MULTILINE | re.DOTALL,
    )
    assert match is not None, f"{name} job block not found"
    return match.group("body")


def test_pr_path_is_non_publishing_and_tag_path_is_canonical_only() -> None:
    workflow = WORKFLOW.read_text()
    header = workflow.split("\njobs:\n", 1)[0]
    assert "pull_request:" in header
    assert "workflow_dispatch:" in header
    assert 'tags:\n      - "v[0-9]+.[0-9]+.[0-9]+"' in header
    assert "permissions: {}" in header

    dry = _job(workflow, "dry-run", "validate-build")
    assert "github.event_name != 'push'" in dry
    assert "github.ref_type != 'tag'" not in dry
    assert "make release-dry-run" in dry
    assert "bash scripts/bootstrap-tools.sh" in dry
    assert "contents: read" in dry
    assert "id-token: write" not in dry
    assert "contents: write" not in dry

    for name, next_name in (
        ("validate-build", "build-attest"),
        ("build-attest", "publish-pypi"),
        ("publish-pypi", "publish-github"),
        ("publish-github", None),
    ):
        block = _job(workflow, name, next_name)
        assert "github.ref_type == 'tag'" in block
        assert "github.event_name == 'push'" in block
        assert "github.repository == 'PranavMishra28/irrevon'" in block
        assert "github.actor == github.repository_owner" in block


def test_untrusted_build_is_separate_from_oidc_and_publication_permissions() -> None:
    workflow = WORKFLOW.read_text()
    build = _job(workflow, "validate-build", "build-attest")
    attest = _job(workflow, "build-attest", "publish-pypi")
    pypi = _job(workflow, "publish-pypi", "publish-github")
    github_release = _job(workflow, "publish-github")

    assert "make launch-audit" in build
    assert "bash scripts/bootstrap-tools.sh" in build
    assert "id-token: write" not in build
    assert "attestations: write" not in build
    assert "contents: write" not in build
    assert "enable-cache: false" in build
    assert "package-manager-cache: false" in build

    assert "needs: validate-build" in attest
    assert "actions/download-artifact@" in attest
    assert "actions/checkout@" not in attest
    assert "run:" not in attest
    assert "id-token: write" in attest
    assert "attestations: write" in attest
    assert "contents: read" in attest

    assert "environment: release" in pypi
    assert "id-token: write" in pypi
    assert "contents: write" not in pypi
    assert "packages-dir: packages" in pypi

    assert "needs: [build-attest, publish-pypi]" in github_release
    assert "environment: release" in github_release
    assert "contents: write" in github_release
    assert "id-token: write" not in github_release


def test_release_refuses_mismatched_versions_and_attests_every_evidence_file() -> None:
    workflow = WORKFLOW.read_text()
    build = _job(workflow, "validate-build", "build-attest")
    attest = _job(workflow, "build-attest", "publish-pypi")
    assert "tag is not exactly vMAJOR.MINOR.PATCH" in build
    assert 'git cat-file -t "refs/tags/$TAG_NAME"' in build
    assert 'git merge-base --is-ancestor "$TAG_NAME^{}" origin/main' in build
    assert 'test "v$package_version" = "$TAG_NAME"' in build
    assert "*dev*|*+*" in build
    assert 'test -z "$(git status --porcelain)"' in build
    for path in ("dist/*.whl", "dist/*.tar.gz", "dist/SHA256SUMS", "dist/irrevon.spdx.json"):
        assert path in attest


def test_makefile_exposes_non_publishing_launch_and_release_dry_runs() -> None:
    makefile = MAKEFILE.read_text()
    assert "\nlaunch-audit:\n\tbash scripts/launch-audit.sh" in makefile
    assert "\nrelease-dry-run:\n\tbash scripts/release-dry-run.sh" in makefile
