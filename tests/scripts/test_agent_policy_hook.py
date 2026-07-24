"""Fail-closed contract for the scoped v0.1.0 agent launch authorization."""

from __future__ import annotations

import json
import subprocess
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
HOOK = ROOT / ".cursor" / "hooks" / "deny.sh"
REPO = "PranavMishra28/irrevon"


def decision(command: str) -> str:
    completed = subprocess.run(
        ["bash", str(HOOK)],
        input=json.dumps({"command": command}),
        check=True,
        capture_output=True,
        text=True,
    )
    return json.loads(completed.stdout)["permission"]


def test_exact_launch_api_surfaces_are_allowed() -> None:
    allowed = (
        f"IRREVON_V010_LAUNCH=1 gh api -X PUT repos/{REPO}/rulesets/123 --input /tmp/ruleset.json",
        (
            f"IRREVON_V010_LAUNCH=1 gh api --method=PUT "
            f"repos/{REPO}/actions/permissions -f enabled_repositories=selected"
        ),
        f"IRREVON_V010_LAUNCH=1 gh api -XPUT repos/{REPO}/private-vulnerability-reporting",
        (
            f"IRREVON_V010_LAUNCH=1 gh api -X PUT "
            f"repos/{REPO}/environments/release --input /tmp/environment.json"
        ),
        (
            f"IRREVON_V010_LAUNCH=1 gh api -X POST "
            f"repos/{REPO}/actions/runs/456/pending_deployments --input /tmp/review.json"
        ),
        f"IRREVON_V010_LAUNCH=1 gh api -X POST repos/{REPO}/discussions -f title=Welcome",
        f"IRREVON_V010_LAUNCH=1 gh api -X PATCH repos/{REPO} -f has_discussions=true",
        (
            f"IRREVON_V010_LAUNCH=1 gh api -X PATCH repos/{REPO} "
            "-f 'security_and_analysis[secret_scanning][status]=enabled'"
        ),
    )
    for command in allowed:
        assert decision(command) == "allow", command


def test_neighboring_api_mutations_remain_denied() -> None:
    denied = (
        "gh api -X PUT repos/another-owner/irrevon/rulesets/123 --input /tmp/ruleset.json",
        f"gh api -X DELETE repos/{REPO}",
        f"gh api -X PATCH repos/{REPO} -f visibility=private",
        f"gh api -X POST repos/{REPO}/releases -f tag_name=v0.2.0",
        f"gh api -X PUT repos/{REPO}/environments/production",
        f"IRREVON_V010_LAUNCH=1 gh api -X PUT repos/{REPO}/environments/release/secrets/NAME",
        f"IRREVON_V010_LAUNCH=1 gh api -X POST repos/{REPO}/releases -f has_discussions=true",
        f"gh api --method=PATCH repos/{REPO} -f has_discussions=true",
        f"gh api -XPATCH repos/{REPO} -f has_discussions=true",
        (
            f"IRREVON_V010_LAUNCH=1 gh api -X PATCH repos/{REPO} "
            "-f has_discussions=true -f visibility=private"
        ),
        (
            f"IRREVON_V010_LAUNCH=1 gh api -X PUT repos/{REPO}/rulesets/123 "
            f"--input /tmp/ruleset.json; gh repo delete {REPO}"
        ),
        "gh api graphql -f 'query=mutation { deleteRepository(input: {}) { clientMutationId } }'",
    )
    for command in denied:
        assert decision(command) == "deny", command


def test_direct_release_commands_remain_workflow_only() -> None:
    denied = (
        f"gh release view v0.1.0 --repo {REPO}",
        f"gh release upload v0.1.0 dist/irrevon.whl --repo={REPO}",
        f"gh release create v0.2.0 --repo {REPO}",
        "gh release create v0.1.0 --repo another-owner/irrevon",
        f"gh release delete v0.1.0 --repo {REPO}",
        f"gh release create v0.1.0 --repo {REPO}; gh repo delete {REPO}",
    )
    for command in denied:
        assert decision(command) == "deny", command


def test_tags_and_direct_publication_remain_fail_closed() -> None:
    assert decision("IRREVON_V010_LAUNCH=1 git tag -a v0.1.0 deadbeef -m release") == "allow"
    assert decision("git tag --verify v0.1.0") == "allow"
    assert decision("git tag -a v0.1.0 deadbeef -m release") == "deny"
    assert decision("git tag -a v0.2.0 deadbeef -m release") == "deny"
    assert decision("git push origin refs/tags/v0.2.0") == "deny"
    assert decision("twine upload dist/*") == "deny"
    assert decision("uv publish") == "deny"
    assert decision("git push --force origin main") == "deny"
    assert decision("git push origin -f") == "deny"


def test_local_vercel_mutations_and_credentials_remain_denied() -> None:
    assert decision("vercel deploy --prod") == "deny"
    assert decision("vc promote deployment.example") == "deny"

    completed = subprocess.run(
        ["bash", str(HOOK)],
        input=json.dumps({"file_path": "/tmp/.env"}),
        check=True,
        capture_output=True,
        text=True,
    )
    assert json.loads(completed.stdout)["permission"] == "deny"
