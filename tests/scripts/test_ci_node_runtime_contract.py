"""Contract for the declared Node runtime in active GitHub workflows."""

from __future__ import annotations

import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
CI_WORKFLOW = ROOT / ".github" / "workflows" / "ci.yml"
NIGHTLY_WORKFLOW = ROOT / ".github" / "workflows" / "nightly.yml"

SETUP_NODE = "actions/setup-node@820762786026740c76f36085b0efc47a31fe5020 # v7.0.0"


def _job_block(workflow: str, job: str, next_job: str | None = None) -> str:
    boundary = rf"(?=^  {re.escape(next_job)}:\n)" if next_job is not None else r"\Z"
    match = re.search(
        rf"^  {re.escape(job)}:\n(?P<body>.*?){boundary}",
        workflow,
        flags=re.MULTILINE | re.DOTALL,
    )
    assert match is not None, f"{job} job block not found"
    return match.group("body")


def _assert_runtime_before_corepack(block: str, version_file: str) -> None:
    setup = f"- uses: {SETUP_NODE}"
    corepack = "- run: corepack enable"
    assert block.count(setup) == 1
    assert block.count(f"node-version-file: {version_file}") == 1
    assert block.count(corepack) == 1
    assert block.index(setup) < block.index(f"node-version-file: {version_file}")
    assert block.index(f"node-version-file: {version_file}") < block.index(corepack)


def test_ci_corepack_jobs_use_their_declared_node_runtime() -> None:
    workflow = CI_WORKFLOW.read_text()
    jobs = (
        ("web-check", "web-test", "web/.nvmrc"),
        ("web-test", "web-e2e", "web/.nvmrc"),
        ("web-e2e", "site-check", "web/.nvmrc"),
        ("site-check", "site-test", "site/.nvmrc"),
        ("site-test", "web-e2e-live", "site/.nvmrc"),
        ("web-e2e-live", "workflow-security", "web/.nvmrc"),
    )
    for job, next_job, version_file in jobs:
        _assert_runtime_before_corepack(_job_block(workflow, job, next_job), version_file)

    assert workflow.count("- run: corepack enable") == len(jobs)
    assert workflow.count(f"- uses: {SETUP_NODE}") == len(jobs)


def test_nightly_wheel_build_uses_the_workbench_node_runtime() -> None:
    workflow = NIGHTLY_WORKFLOW.read_text()
    block = _job_block(workflow, "wheel-smoke", "report-failure")
    _assert_runtime_before_corepack(block, "web/.nvmrc")

    assert workflow.count("- run: corepack enable") == 1
    assert workflow.count(f"- uses: {SETUP_NODE}") == 1
