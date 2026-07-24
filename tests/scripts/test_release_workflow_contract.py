"""Fail-closed contract for the dormant package-release workflow.

This static orchestration test prevents a skipped or no-op dispatch from being
misread as release readiness. Before human activation, the workflow must
always reach one unconditional refusal and expose no publication capability.
"""

from __future__ import annotations

import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
WORKFLOW = ROOT / ".github" / "workflows" / "release.yml"
MAKEFILE = ROOT / "Makefile"
ACTIONLINT_CONFIG = ROOT / ".github" / "actionlint.yaml"


def _active_yaml(workflow: str) -> str:
    """Discard the explicitly non-executable commented release outline."""
    return "\n".join(line for line in workflow.splitlines() if not line.lstrip().startswith("#"))


def _job_block(active_workflow: str, job: str) -> str:
    match = re.search(
        rf"^  {re.escape(job)}:\n(?P<body>.*)\Z",
        active_workflow,
        flags=re.MULTILINE | re.DOTALL,
    )
    assert match is not None, f"{job} job block not found"
    return match.group("body")


def _target_recipe(makefile: str, target: str) -> list[str]:
    marker = f"\n{target}:\n"
    assert marker in makefile, f"{target} target not found"
    block = makefile.split(marker, 1)[1].split("\n\n", 1)[0]
    return [line.strip() for line in block.splitlines() if line.startswith("\t")]


def test_release_workflow_is_manual_only_unskippable_and_least_privilege() -> None:
    workflow = WORKFLOW.read_text(encoding="utf-8")
    active = _active_yaml(workflow)
    header = active.split("\njobs:\n", 1)[0]
    job = _job_block(active, "release-gate")

    assert re.search(r"^on:\n  workflow_dispatch:\n", header, flags=re.MULTILINE)
    assert not re.search(
        r"^  (push|pull_request|schedule|workflow_call|release):",
        header,
        flags=re.MULTILINE,
    )
    assert "inputs:" not in header
    assert "permissions: {}" in header
    job_ids = re.findall(
        r"^  ([A-Za-z0-9_-]+):\n",
        active.split("\njobs:\n", 1)[1],
        flags=re.MULTILINE,
    )
    assert job_ids == ["release-gate"]
    assert job.count("permissions:\n      contents: read") == 1
    assert "persist-credentials: false" in job
    assert "if:" not in active
    assert "continue-on-error:" not in active
    assert "environment:" not in active


def test_only_checkout_and_the_inert_release_gate_are_active() -> None:
    workflow = WORKFLOW.read_text(encoding="utf-8")
    active = _active_yaml(workflow)
    job = _job_block(active, "release-gate")

    assert "${{" not in active
    assert "secrets." not in active
    assert "vars." not in active
    assert "github." not in active
    assert not re.search(r"^\s+env:", active, flags=re.MULTILINE)
    assert not re.search(
        r"^\s+(id-token|attestations|packages|actions):\s+write$",
        active,
        flags=re.MULTILINE,
    )
    assert "contents: write" not in active

    uses = re.findall(r"^\s+- uses:\s*(\S+)", job, flags=re.MULTILINE)
    assert uses == ["actions/checkout@3d3c42e5aac5ba805825da76410c181273ba90b1"]
    run_commands = re.findall(r"^\s+run:\s*(.+)$", job, flags=re.MULTILINE)
    assert run_commands == ["make release-gate"]

    forbidden_active_steps = (
        "upload-artifact",
        "download-artifact",
        "attest-build-provenance",
        "gh-action-pypi-publish",
        "gh release",
        "git tag",
        "uv build",
        "make dist",
    )
    assert all(token not in active for token in forbidden_active_steps)


def test_reserved_release_entrypoint_is_an_unconditional_refusal() -> None:
    makefile = MAKEFILE.read_text(encoding="utf-8")
    recipe = _target_recipe(makefile, "release-gate")

    assert recipe == [
        '@echo "release-gate: REFUSED - distribution is a fail-closed skeleton." >&2',
        '@echo "Every public-release gate item and a separate human activation are required." >&2',
        "@exit 1",
    ]


def test_actionlint_has_no_stale_release_bypass() -> None:
    config = ACTIONLINT_CONFIG.read_text(encoding="utf-8")
    assert "release.yml" not in config
    assert "constant expression" not in config
    assert "ignore:" not in config
