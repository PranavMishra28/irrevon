"""Fail-closed contract for the dormant M7 benchmark workflow.

This is intentionally a static orchestration test. Before human Stage-B
activation, the workflow must be structurally incapable of reporting a green
benchmark run: no secret and no checked-in file may bypass the reserved Make
entrypoint's unconditional refusal.
"""

from __future__ import annotations

import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
WORKFLOW = ROOT / ".github" / "workflows" / "benchmark.yml"
MAKEFILE = ROOT / "Makefile"


def _job_block(workflow: str, job: str) -> str:
    match = re.search(
        rf"^  {re.escape(job)}:\n(?P<body>.*)\Z",
        workflow,
        flags=re.MULTILINE | re.DOTALL,
    )
    assert match is not None, f"{job} job block not found"
    return match.group("body")


def _target_recipe(makefile: str, target: str) -> list[str]:
    marker = f"\n{target}:\n"
    assert marker in makefile, f"{target} target not found"
    block = makefile.split(marker, 1)[1].split("\n\n", 1)[0]
    return [line.strip() for line in block.splitlines() if line.startswith("\t")]


def test_benchmark_workflow_remains_manual_approval_gated_and_least_privilege() -> None:
    workflow = WORKFLOW.read_text(encoding="utf-8")
    header = workflow.split("\njobs:\n", 1)[0]
    job = _job_block(workflow, "bench")

    assert re.search(r"^on:\n  workflow_dispatch:\n", header, flags=re.MULTILINE)
    assert not re.search(r"^  (push|pull_request|schedule|workflow_call):", header, re.MULTILINE)
    assert "environment: benchmark" in job
    assert workflow.count("permissions:\n  contents: read") == 1
    assert job.count("permissions:\n      contents: read") == 1
    assert "persist-credentials: false" in job
    assert "continue-on-error:" not in job


def test_no_secret_or_file_condition_can_bypass_the_only_executable_body() -> None:
    workflow = WORKFLOW.read_text(encoding="utf-8")
    job = _job_block(workflow, "bench")
    active_job = "\n".join(
        line for line in job.splitlines() if not line.lstrip().startswith("#")
    )

    # Secrets are not merely empty-checked: the dormant workflow cannot read
    # one at all, so configuring one cannot change the refusal.
    assert "secrets." not in workflow
    assert "${{ vars." not in workflow

    # File/directory existence was the historical bypass. No conditional gate
    # or registration-path probe is allowed in the skeleton.
    assert "pyproject.toml" not in workflow
    assert "docs/registrations" not in workflow
    assert not re.search(r"\b(if|test)\s+(?:!?\s*)?\[", workflow)
    assert "if:" not in active_job

    run_commands = re.findall(r"^\s+run:\s*(.+)$", active_job, flags=re.MULTILINE)
    assert run_commands == ["make benchmark-stage-b"]


def test_reserved_stage_b_entrypoint_is_an_unconditional_inert_refusal() -> None:
    makefile = MAKEFILE.read_text(encoding="utf-8")
    recipe = _target_recipe(makefile, "benchmark-stage-b")

    # Exact recipe lock: before human activation there is no harness, provider,
    # shell conditional, variable expansion, or artifact-producing command
    # before the mandatory nonzero exit.
    assert recipe == [
        '@echo "benchmark-stage-b: REFUSED - the M7 workflow is a fail-closed skeleton." >&2',
        '@echo "A human Stage-B freeze and a real registered benchmark recipe are required." >&2',
        "@exit 1",
    ]
