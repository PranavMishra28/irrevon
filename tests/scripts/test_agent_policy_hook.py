"""Fail-closed contract for the scoped v0.1.0 agent launch authorization."""

from __future__ import annotations

import json
import subprocess
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
HOOK = ROOT / ".cursor" / "hooks" / "deny.sh"
REPO = "PranavMishra28/irrevon"
WELCOME_PAYLOAD = Path("/tmp/irrevon-v010-welcome-discussion.json")
WELCOME_QUERY = (
    "mutation CreateDiscussion($repositoryId: ID!, $categoryId: ID!, "
    "$title: String!, $body: String!) { createDiscussion(input: "
    "{repositoryId: $repositoryId, categoryId: $categoryId, title: $title, "
    "body: $body}) { discussion { url } } }"
)
WELCOME_BODY = (
    "Use Discussions for questions, ideas, design feedback, integrations, "
    "experiments, and advice. Use Issues for reproducible bugs, documentation "
    "defects, benchmark-integrity concerns, and scoped work. Pull requests are "
    "for implementations. Report security vulnerabilities privately through "
    "GitHub Private Vulnerability Reporting. This community has no support SLA; "
    "participation is governed by the Code of Conduct. Never post credentials, "
    "private payloads, benchmark holdouts, or personal data."
)


def decision(command: str) -> str:
    completed = subprocess.run(
        ["bash", str(HOOK)],
        input=json.dumps({"command": command}),
        check=True,
        capture_output=True,
        text=True,
    )
    return json.loads(completed.stdout)["permission"]


def welcome_payload(**overrides: object) -> dict[str, object]:
    variables: dict[str, object] = {
        "repositoryId": "R_kgDOTeu25A",
        "categoryId": "DIC_kwDOTeu25M4DB51i",
        "title": "Welcome to the Irrevon community",
        "body": WELCOME_BODY,
    }
    variables.update(overrides.pop("variables", {}))  # type: ignore[arg-type]
    payload: dict[str, object] = {"query": WELCOME_QUERY, "variables": variables}
    payload.update(overrides)
    return payload


def welcome_decision(payload: dict[str, object]) -> str:
    previous = WELCOME_PAYLOAD.read_bytes() if WELCOME_PAYLOAD.exists() else None
    try:
        WELCOME_PAYLOAD.write_text(json.dumps(payload), encoding="utf-8")
        command = (
            "IRREVON_V010_LAUNCH=1 gh api graphql --input /tmp/irrevon-v010-welcome-discussion.json"
        )
        return decision(command)
    finally:
        if previous is None:
            WELCOME_PAYLOAD.unlink(missing_ok=True)
        else:
            WELCOME_PAYLOAD.write_bytes(previous)


def test_only_exact_welcome_discussion_graphql_payload_is_allowed() -> None:
    assert welcome_decision(welcome_payload()) == "allow"

    invalid_payloads = (
        welcome_payload(variables={"repositoryId": "R_wrong"}),
        welcome_payload(variables={"categoryId": "DIC_wrong"}),
        welcome_payload(variables={"title": "Different title"}),
        welcome_payload(query="mutation { deleteRepository(input: {}) { clientMutationId } }"),
        welcome_payload(unexpected=True),
        welcome_payload(variables={"unexpected": True}),
    )
    for payload in invalid_payloads:
        assert welcome_decision(payload) == "deny", payload

    assert (
        decision(
            "gh api graphql -f "
            "'query=mutation { deleteRepository(input: {}) { clientMutationId } }'"
        )
        == "deny"
    )
    assert (
        decision("IRREVON_V010_LAUNCH=1 gh api graphql --input /tmp/different-discussion.json")
        == "deny"
    )


def test_exact_launch_api_surfaces_are_allowed() -> None:
    allowed = (
        (
            f"IRREVON_V010_LAUNCH=1 gh api -X PUT repos/{REPO}/rulesets/19426315 "
            "--input /tmp/irrevon-v010-ruleset.json"
        ),
        (
            f"IRREVON_V010_LAUNCH=1 gh api --method=PUT "
            f"repos/{REPO}/actions/permissions "
            "--input /tmp/irrevon-v010-actions-permissions.json"
        ),
        (
            f"IRREVON_V010_LAUNCH=1 gh api -X PUT "
            f"repos/{REPO}/actions/permissions/selected-actions "
            "--input /tmp/irrevon-v010-selected-actions.json"
        ),
        (
            f"IRREVON_V010_LAUNCH=1 gh api -X PUT "
            f"repos/{REPO}/environments/release "
            "--input /tmp/irrevon-v010-release-environment.json"
        ),
        (
            f"IRREVON_V010_LAUNCH=1 IRREVON_RELEASE_RUN_ID=456 gh api -X POST "
            f"repos/{REPO}/actions/runs/456/pending_deployments "
            "--input /tmp/irrevon-v010-deployment-review.json"
        ),
        f"IRREVON_V010_LAUNCH=1 gh api -X POST repos/{REPO}/discussions -f title=Welcome",
        f"IRREVON_V010_LAUNCH=1 gh api -X PATCH repos/{REPO} -f has_discussions=true",
        (
            f"IRREVON_V010_LAUNCH=1 gh api -X PATCH repos/{REPO} "
            "-f security_and_analysis[secret_scanning_non_provider_patterns][status]=enabled"
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
            f"IRREVON_V010_LAUNCH=1 gh api -X PUT repos/{REPO}/rulesets/19426315 "
            f"--input /tmp/irrevon-v010-ruleset.json; gh repo delete {REPO}"
        ),
        "gh api graphql -f 'query=mutation { deleteRepository(input: {}) { clientMutationId } }'",
        (
            f"IRREVON_V010_LAUNCH=1 gh api -X PUT repos/{REPO}/rulesets/999 "
            "--input /tmp/irrevon-v010-ruleset.json"
        ),
        (
            f"IRREVON_V010_LAUNCH=1 gh api -X PUT repos/{REPO}/rulesets/19426315 "
            "--input /tmp/another-payload.json"
        ),
        (
            f"IRREVON_V010_LAUNCH=1 gh api -X PUT repos/{REPO}/rulesets/19426315 "
            "--input /tmp/irrevon-v010-ruleset.json -F body=@.env"
        ),
        (
            f"IRREVON_V010_LAUNCH=1 gh api -X PUT repos/{REPO}/rulesets/19426315 "
            "--input /tmp/irrevon-v010-ruleset.json "
            "--input /tmp/irrevon-v010-ruleset.json"
        ),
        (
            f"IRREVON_V010_LAUNCH=1 gh api -X POST "
            f"repos/{REPO}/actions/runs/456/pending_deployments "
            "--input /tmp/irrevon-v010-deployment-review.json"
        ),
        (
            f"IRREVON_V010_LAUNCH=1 IRREVON_RELEASE_RUN_ID=789 gh api -X POST "
            f"repos/{REPO}/actions/runs/456/pending_deployments "
            "--input /tmp/irrevon-v010-deployment-review.json"
        ),
        f"IRREVON_V010_LAUNCH=1 gh api -X PATCH repos/{REPO} -f has_issues=false",
        f"IRREVON_V010_LAUNCH=1 gh api -X TRACE repos/{REPO}",
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
    assert decision("IRREVON_V010_LAUNCH=1 git tag -a v0.1.0 origin/main -m release") == "allow"
    assert decision("git tag --verify v0.1.0") == "allow"
    assert decision("git tag -a v0.1.0 deadbeef -m release") == "deny"
    assert decision("IRREVON_V010_LAUNCH=1 git tag -a v0.1.0 HEAD -m release") == "deny"
    assert decision("IRREVON_V010_LAUNCH=1 git tag -a v0.1.0 deadbeef -m release") == "deny"
    assert decision("git tag -a v0.2.0 deadbeef -m release") == "deny"
    assert decision("git push origin v0.1.0") == "deny"
    assert decision("IRREVON_V010_LAUNCH=1 git push origin v0.1.0") == "deny"
    assert decision("IRREVON_V010_LAUNCH=1 git push origin refs/tags/v0.1.0") == "allow"
    destination_override = "IRREVON_V010_LAUNCH=1 git push origin refs/tags/v0.1.0:refs/tags/latest"
    assert decision(destination_override) == "deny"
    assert decision("git push origin refs/tags/v0.2.0") == "deny"
    assert decision("git push origin main") == "deny"
    assert decision("git push origin HEAD:main") == "deny"
    assert decision("git push origin feature:refs/heads/main") == "deny"
    assert decision("git push origin +HEAD:refs/heads/main") == "deny"
    assert decision("git push --delete origin old-branch") == "deny"
    assert decision("git push origin :old-branch") == "deny"
    assert decision("twine upload dist/*") == "deny"
    assert decision("uv publish") == "deny"
    assert decision("git push --force origin main") == "deny"
    assert decision("git push origin -f") == "deny"


def test_local_vercel_mutations_and_credentials_remain_denied() -> None:
    assert decision("vercel deploy --prod") == "deny"
    assert decision("vercel --prod") == "deny"
    assert decision("vercel") == "deny"
    assert decision("vc promote deployment.example") == "deny"
    assert decision("vc --prod") == "deny"
    assert decision("/usr/local/bin/vercel --prod") == "deny"
    assert decision(f"gh pr merge 23 --repo {REPO} --admin") == "deny"
    assert decision(f"gh pr merge 23 --repo {REPO} --admin=true") == "deny"

    completed = subprocess.run(
        ["bash", str(HOOK)],
        input=json.dumps({"file_path": "/tmp/.env"}),
        check=True,
        capture_output=True,
        text=True,
    )
    assert json.loads(completed.stdout)["permission"] == "deny"


def test_multiline_commands_are_denied_before_allowlist_matching() -> None:
    command = (
        f"IRREVON_V010_LAUNCH=1 gh api -X PATCH repos/{REPO} "
        "-f has_discussions=true\n"
        f"gh repo delete {REPO}"
    )
    assert decision(command) == "deny"
    assert decision(command.replace("\n", "\r\n")) == "deny"
