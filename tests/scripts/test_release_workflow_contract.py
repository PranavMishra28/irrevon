"""Fail-closed contract for the executable, owner-gated release workflow."""

from __future__ import annotations

import json
import os
import re
import subprocess
import tomllib
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
WORKFLOW = ROOT / ".github" / "workflows" / "release.yml"
MAKEFILE = ROOT / "Makefile"
DRY_RUN = ROOT / "scripts" / "release-dry-run.sh"
BOOTSTRAP = ROOT / "scripts" / "bootstrap-tools.sh"
PYPROJECT = ROOT / "pyproject.toml"
UV_LOCK = ROOT / "uv.lock"
WEB_PACKAGE = ROOT / "web" / "package.json"
PACKAGE_README = ROOT / "PACKAGE_README.md"
CHANGELOG = ROOT / "CHANGELOG.md"
CITATION = ROOT / "CITATION.cff"
LICENSING = ROOT / "LICENSING.md"
THIRD_PARTY_NOTICES = ROOT / "THIRD-PARTY-NOTICES.md"


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
    for release_input in (
        "pyproject.toml",
        "hatch_build.py",
        "PACKAGE_README.md",
        "CHANGELOG.md",
        "CITATION.cff",
        "LICENSE",
        "NOTICE",
    ):
        assert f'- "{release_input}"' in header

    dry = _job(workflow, "dry-run", "validate-build")
    assert "github.event_name != 'push'" in dry
    assert "github.ref_type != 'tag'" not in dry
    assert "make release-dry-run" in dry
    assert 'IRREVON_ALLOW_RELEASE_VERSION: "1"' in dry
    assert 'IRREVON_LOCKED_RELEASE_VALIDATION: "1"' in dry
    assert "uv run --locked --group release-validation make check" in dry
    assert "bash scripts/bootstrap-tools.sh" in dry
    assert "contents: read" in dry
    assert "id-token: write" not in dry
    assert "contents: write" not in dry

    for name, next_name in (
        ("validate-build", "build-attest"),
        ("build-attest", "stage-github-release"),
        ("stage-github-release", "publish-pypi"),
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
    attest = _job(workflow, "build-attest", "stage-github-release")
    draft = _job(workflow, "stage-github-release", "publish-pypi")
    pypi = _job(workflow, "publish-pypi", "publish-github")
    github_release = _job(workflow, "publish-github")

    assert "make launch-audit" in build
    assert 'IRREVON_LOCKED_RELEASE_VALIDATION: "1"' in build
    assert "uv run --locked --group release-validation make launch-audit" in build
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

    assert "needs: build-attest" in draft
    assert "environment: release" in draft
    assert "contents: write" in draft
    assert "id-token: write" not in draft
    assert "actions/checkout@" not in draft
    assert "actions/download-artifact@" in draft
    assert 'gh release create "$TAG_NAME"' in draft
    assert "--draft --verify-tag" in draft
    assert "gh release upload" in draft
    assert "--clobber" in draft
    assert "refusing to replace an already-published release" in draft
    assert 'test "$(gh release view "$TAG_NAME" --json isDraft --jq .isDraft)" = "true"' in draft

    assert "needs: stage-github-release" in pypi
    assert "environment: release" in pypi
    assert "id-token: write" in pypi
    assert "contents: write" not in pypi
    assert "packages-dir: packages" in pypi
    assert "PyPI already has conflicting files for this version" in pypi
    assert "published != expected" in pypi
    assert "steps.pypi-state.outputs.publish == 'true'" in pypi

    assert "needs: [stage-github-release, publish-pypi]" in github_release
    assert "environment: release" in github_release
    assert "contents: write" in github_release
    assert "id-token: write" not in github_release
    assert "https://pypi.org/pypi/irrevon/{version}/json" in github_release
    assert "published == expected" in github_release
    assert 'gh release edit "$TAG_NAME" --draft=false --latest' in github_release
    assert "gh release create" not in github_release


def test_release_refuses_mismatched_versions_and_attests_every_evidence_file() -> None:
    workflow = WORKFLOW.read_text()
    build = _job(workflow, "validate-build", "build-attest")
    attest = _job(workflow, "build-attest", "stage-github-release")
    assert "tag is not exactly vMAJOR.MINOR.PATCH" in build
    assert 'git cat-file -t "refs/tags/$TAG_NAME"' in build
    assert 'tagged_commit=$(git rev-parse "$TAG_NAME^{}")' in build
    assert "reviewed_main=$(git rev-parse origin/main)" in build
    assert "checked_out_commit=$(git rev-parse HEAD)" in build
    assert 'test "$checked_out_commit" = "$tagged_commit"' in build
    assert 'test "$checked_out_commit" = "$reviewed_main"' in build
    assert "git merge-base --is-ancestor" not in build
    assert 'test "v$package_version" = "$TAG_NAME"' in build
    assert "*dev*|*+*" in build
    assert 'test -z "$(git status --porcelain)"' in build
    for path in ("dist/*.whl", "dist/*.tar.gz", "dist/SHA256SUMS", "dist/irrevon.spdx.json"):
        assert path in attest


def test_release_notes_are_curated_alpha_copy_with_explicit_evidence_boundaries() -> None:
    workflow = WORKFLOW.read_text()
    draft = _job(workflow, "stage-github-release", "publish-pypi")
    normalized = draft.lower()
    for expected in (
        "initial Alpha release",
        "continuous single-writer reconciliation engine",
        "loopback-only, read-only Workbench",
        "pip install irrevon==0.1.0",
    ):
        assert expected in draft
    for expected in (
        "development evidence is synthetic",
        "preregistration remains an unfrozen draft",
        "provider adapters have not",
        "production readiness",
        "universal exactly-once behavior",
    ):
        assert expected in normalized
    for forbidden in (
        "scientifically validated",
        "production-proven",
        "enterprise-ready",
        "exactly-once guarantee",
    ):
        assert forbidden not in draft


def test_package_facing_copy_is_lifecycle_neutral_and_alpha_scoped() -> None:
    documents = {
        "PACKAGE_README.md": PACKAGE_README.read_text(),
        "CHANGELOG.md": CHANGELOG.read_text(),
        "CITATION.cff": CITATION.read_text(),
        "LICENSING.md": LICENSING.read_text(),
        "THIRD-PARTY-NOTICES.md": THIRD_PARTY_NOTICES.read_text(),
    }
    lifecycle_fragments = (
        "pending publication",
        "Nothing is on any package index",
        "No Irrevon artifact has been published",
        "package-index release exists yet",
        "release candidate",
    )
    for name, text in documents.items():
        for fragment in lifecycle_fragments:
            assert fragment not in text, f"{name} contains lifecycle-bound copy {fragment!r}"

    package_readme = documents["PACKAGE_README.md"]
    normalized_package_readme = " ".join(package_readme.split())
    assert "initial Alpha release" in package_readme
    assert "development evidence is synthetic" in package_readme.lower()
    assert "provider qualification" in normalized_package_readme
    assert "production adoption" in normalized_package_readme

    project = tomllib.loads(PYPROJECT.read_text())
    assert "Development Status :: 3 - Alpha" in project["project"]["classifiers"]
    assert "Typing :: Typed" in project["project"]["classifiers"]
    assert project["project"]["urls"]["Release-notes"].endswith("/releases/tag/v0.1.0")


def test_makefile_exposes_non_publishing_launch_and_release_dry_runs() -> None:
    makefile = MAKEFILE.read_text()
    assert "\nlaunch-audit:\n\tbash scripts/launch-audit.sh" in makefile
    assert "\nrelease-dry-run:\n\tbash scripts/release-dry-run.sh" in makefile


def test_release_dry_run_strictly_checks_pypi_readme_without_publishing() -> None:
    script = DRY_RUN.read_text()
    assert "uv run --locked --group release-validation twine check --strict" in script
    assert "uvx" not in script
    assert "hashes_before=$(sha256sum" in script
    assert "hashes_after=$(sha256sum" in script
    assert 'test "$hashes_before" = "$hashes_after"' in script
    assert script.count('python3 scripts/check-dist-contents.py "$sdist" "$wheel"') == 2
    before = script.index("hashes_before=$(sha256sum")
    twine = script.index("twine check --strict")
    after = script.index("hashes_after=$(sha256sum")
    recheck = script.rindex("python3 scripts/check-dist-contents.py")
    assert before < twine < after < recheck
    assert "IRREVON_ALLOW_RELEASE_VERSION" in script
    for forbidden in ("twine upload", "uv publish", "gh release", "git tag", "git push"):
        assert forbidden not in script


def test_release_python_validators_are_exact_and_lock_resolved() -> None:
    project = tomllib.loads(PYPROJECT.read_text())
    assert project["dependency-groups"]["release-validation"] == [
        "check-jsonschema==0.37.4",
        "pip-audit==2.10.1",
        "spdx-tools==0.8.3",
        "twine==6.2.0",
    ]
    lock = UV_LOCK.read_text()
    assert "release-validation = [" in lock
    assert '{ name = "check-jsonschema", specifier = "==0.37.4" }' in lock
    assert '{ name = "pip-audit", specifier = "==2.10.1" }' in lock
    assert '{ name = "spdx-tools", specifier = "==0.8.3" }' in lock
    assert '{ name = "twine", specifier = "==6.2.0" }' in lock

    bootstrap = BOOTSTRAP.read_text()
    assert 'IRREVON_LOCKED_RELEASE_VALIDATION:-0' in bootstrap
    assert "uv sync --locked --group release-validation" in bootstrap
    locked_branch = bootstrap.split(
        'if [ "${IRREVON_LOCKED_RELEASE_VALIDATION:-0}" = "1" ]; then', 1
    )[1].split("\nelif ", 1)[0]
    assert "uv tool install" not in locked_branch
    assert "pipx install" not in locked_branch
    assert "pip install" not in locked_branch


def test_web_release_build_refuses_non_node_24_before_vite() -> None:
    package = json.loads(WEB_PACKAGE.read_text())
    assert package["engines"]["node"] == ">=24.0.0 <25"
    assert package["scripts"]["build"] == "vite build"
    prebuild = package["scripts"]["prebuild"]
    assert "major!==24" in prebuild
    assert "process.exit(1)" in prebuild
    assert "release web builds require Node 24.x" in prebuild


def test_final_version_dry_run_requires_explicit_candidate_validation() -> None:
    env = os.environ.copy()
    env.pop("IRREVON_ALLOW_RELEASE_VERSION", None)
    result = subprocess.run(
        ["bash", str(DRY_RUN)],
        cwd=ROOT,
        env=env,
        text=True,
        capture_output=True,
        check=False,
    )
    assert result.returncode != 0
    assert "refusing non-development version 0.1.0" in result.stderr
    assert "candidate validation only; never publishes" in result.stderr


def test_launch_audit_uses_locked_auditor_on_frozen_hashed_runtime_graph() -> None:
    script = (ROOT / "scripts" / "launch-audit.sh").read_text()
    assert "uv export --frozen --no-dev --no-emit-project" in script
    assert "uv run --locked --group release-validation pip-audit" in script
    assert "--require-hashes --disable-pip --requirement" in script
    assert "audit_requirements=$(mktemp)" in script
    assert 'rm -f -- "$audit_requirements"' in script
