"""Fail-closed contract for the dormant M4 sandbox workflow.

The workflow must be structurally incapable of reporting a green sandbox
contract before human activation: neither dispatch input, configured state,
nor a checked-in file may bypass the reserved Make refusal.
"""

from __future__ import annotations

import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
WORKFLOW = ROOT / ".github" / "workflows" / "sandbox.yml"
MAKEFILE = ROOT / "Makefile"


def _active_yaml(workflow: str) -> str:
    """Return executable YAML, excluding design-only comment lines."""
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


def test_sandbox_workflow_is_manual_approval_gated_and_least_privilege() -> None:
    workflow = WORKFLOW.read_text(encoding="utf-8")
    active = _active_yaml(workflow)
    header = active.split("\njobs:\n", 1)[0]
    job = _job_block(active, "sandbox-contract")

    assert re.search(r"^on:\n  workflow_dispatch:\n", header, flags=re.MULTILINE)
    assert not re.search(
        r"^  (push|pull_request|schedule|workflow_call|release):",
        header,
        flags=re.MULTILINE,
    )
    assert re.search(
        r"^    inputs:\n"
        r"      reason:\n"
        r"(?:        .*\n)*?"
        r"        required: true$",
        header,
        flags=re.MULTILINE,
    )
    assert "environment: sandbox" in job
    assert workflow.count("permissions:\n  contents: read") == 1
    assert job.count("permissions:\n      contents: read") == 1
    assert "persist-credentials: false" in job
    assert "if:" not in active
    assert "continue-on-error:" not in active


def test_only_checkout_and_the_inert_m4_refusal_are_active() -> None:
    workflow = WORKFLOW.read_text(encoding="utf-8")
    active = _active_yaml(workflow)
    job = _job_block(active, "sandbox-contract")

    # The required reason remains run-log metadata at dispatch time; no input,
    # secret, variable, or environment value reaches the executable job.
    assert "${{" not in active
    assert "secrets." not in workflow
    assert "vars." not in workflow
    assert not re.search(r"^\s+env:", active, flags=re.MULTILINE)

    uses = re.findall(r"^\s+- uses:\s*(\S+)", job, flags=re.MULTILINE)
    assert uses == ["actions/checkout@3d3c42e5aac5ba805825da76410c181273ba90b1"]
    run_commands = re.findall(r"^\s+run:\s*(.+)$", job, flags=re.MULTILINE)
    assert run_commands == ["make sandbox-stage-m4"]

    # Historical file/secret guards made the skeleton conditionally green.
    # Nothing active may probe repository state or provide a second body.
    forbidden_active = (
        "grep ",
        "test ",
        "pyproject.toml",
        "C2_SANDBOX",
        "make sandbox-contract",
        "run: |",
    )
    assert all(token not in active for token in forbidden_active)


def test_reserved_m4_entrypoint_is_an_unconditional_inert_refusal() -> None:
    makefile = MAKEFILE.read_text(encoding="utf-8")
    recipe = _target_recipe(makefile, "sandbox-stage-m4")

    assert recipe == [
        '@echo "sandbox-stage-m4: REFUSED - the M4 workflow is a fail-closed skeleton." >&2',
        '@echo "Stage A and every human sandbox-activation gate must close first." >&2',
        "@exit 1",
    ]
