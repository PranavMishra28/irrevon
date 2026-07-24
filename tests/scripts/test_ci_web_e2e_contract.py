"""Fail-closed contract for the required full-workbench browser gate."""

from __future__ import annotations

import json
import os
import re
import subprocess
import textwrap
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
WORKFLOW = ROOT / ".github" / "workflows" / "ci.yml"


def _workflow_text() -> str:
    return WORKFLOW.read_text()


def _job_block(workflow: str, job: str, next_job: str | None = None) -> str:
    boundary = rf"(?=^  {re.escape(next_job)}:\n)" if next_job is not None else r"\Z"
    match = re.search(
        rf"^  {re.escape(job)}:\n(?P<body>.*?){boundary}",
        workflow,
        flags=re.MULTILINE | re.DOTALL,
    )
    assert match is not None, f"{job} job block not found"
    return match.group("body")


def _aggregator_script(workflow: str) -> str:
    block = _job_block(workflow, "ci-required")
    marker = "        run: |\n"
    assert marker in block
    script = block.split(marker, 1)[1]
    return textwrap.dedent(script)


def _run_aggregator(*, web_changed: bool, web_e2e_result: str) -> subprocess.CompletedProcess[str]:
    workflow = _workflow_text()
    results = {
        "changes": {"result": "success"},
        "docs": {"result": "success"},
        "dco": {"result": "success"},
        "dependency-review": {"result": "success"},
        "py-check": {"result": "skipped"},
        "py-test": {"result": "skipped"},
        "py-test-integration": {"result": "skipped"},
        "web-check": {"result": "success" if web_changed else "skipped"},
        "web-test": {"result": "success" if web_changed else "skipped"},
        "web-e2e": {"result": web_e2e_result},
        "site-check": {"result": "skipped"},
        "site-test": {"result": "skipped"},
        "web-e2e-live": {"result": "skipped"},
        "workflow-security": {"result": "skipped"},
    }
    env = os.environ | {
        "NEEDS": json.dumps(results),
        "CODE": "false",
        "WEB": "true" if web_changed else "false",
        "SITE": "false",
        "LIVE": "false",
        "WORKFLOWS": "false",
        "PY_EXISTS": "true",
        "WEB_EXISTS": "true",
        "SITE_EXISTS": "true",
        "EVENT_NAME": "pull_request",
    }
    return subprocess.run(
        ["bash", "-c", _aggregator_script(workflow)],
        cwd=ROOT,
        env=env,
        text=True,
        capture_output=True,
        check=False,
    )


def test_web_e2e_job_uses_the_pinned_make_surface_and_web_filter() -> None:
    workflow = _workflow_text()
    block = _job_block(workflow, "web-e2e", "site-check")
    assert "needs: [changes, web-test]" in block
    assert "needs.changes.outputs.web_exists == 'true'" in block
    assert "needs.changes.outputs.web == 'true'" in block
    assert "- run: make web-e2e" in block

    before_jobs = workflow.split("\njobs:\n", 1)[0]
    assert "paths:" not in before_jobs

    makefile = (ROOT / "Makefile").read_text()
    target = makefile.split("\nweb-e2e:\n", 1)[1].split("\n\n", 1)[0]
    assert "playwright install chromium --only-shell" in target
    assert "playwright test --project=e2e --project=a11y" in target
    assert "check-all: web-check web-test web-e2e" in makefile


def test_ci_required_rejects_skipped_browser_gate_for_web_change() -> None:
    result = _run_aggregator(web_changed=True, web_e2e_result="skipped")
    assert result.returncode == 1
    assert "FAIL: web-e2e result=skipped (its slice changed)" in result.stdout


def test_ci_required_accepts_legitimate_non_web_skip() -> None:
    result = _run_aggregator(web_changed=False, web_e2e_result="skipped")
    assert result.returncode == 0, result.stdout + result.stderr
    assert "ci-required: all gates accounted for" in result.stdout
