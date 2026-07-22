#!/usr/bin/env bash
# setup-repo-settings.sh — OWNER-RUN repository settings bootstrap.
#
# Implements the ordered owner settings checklist in docs/ci.md ("Owner settings
# checklist"). WHY OWNER-RUN: agents in this repo are hook-blocked from every
# mutating GitHub API call (.cursor/hooks/deny.sh denies `gh api` with
# PATCH/PUT/DELETE, `gh repo edit`, `gh secret`, `gh release`; see
# docs/security-policy.md). Repository settings are a human-only, one-way-door
# concern — this script only packages the checklist so the owner runs it once.
#
# HOW TO RUN (owner, `gh` CLI authenticated with admin rights on the repo):
#   bash scripts/setup-repo-settings.sh            # phase 1 — run now
#   bash scripts/setup-repo-settings.sh --phase2   # ONLY after `ci-required`
#                                                  # has reported green on a real
#                                                  # PR (the script verifies this
#                                                  # and refuses otherwise)
#
# IDEMPOTENT: every mutation is preceded by a read of the current state and is
# skipped when the setting is already applied — safe to re-run at any time.
# Ends with a read-back verification section printing each setting's final state.
#
# Endpoints verified against the GitHub REST docs on 2026-07-21:
#   PATCH /repos/{owner}/{repo}                                  (security_and_analysis)
#   PUT   /repos/{owner}/{repo}/vulnerability-alerts             (Dependabot alerts)
#   PUT   /repos/{owner}/{repo}/automated-security-fixes         (Dependabot security updates)
#   PUT   /repos/{owner}/{repo}/actions/permissions/workflow     (default token perms)
#   PUT   /repos/{owner}/{repo}/actions/permissions/fork-pr-contributor-approval
#   POST  /repos/{owner}/{repo}/rulesets                         (create branch ruleset)
#   PUT   /repos/{owner}/{repo}/rulesets/{ruleset_id}            (phase-2 rule update)
#
# NOT covered here (remain manual UI steps — no complete API surface):
#   - Actions allowlist ("Allow <owner> and select non-<owner> actions" with
#     `astral-sh/setup-uv@*`) and the "Require actions to be pinned to a
#     full-length commit SHA" checkbox (docs/ci.md checklist item 3).
#   - CodeQL default setup, private vulnerability reporting (items 7–8).
set -euo pipefail

# Derive the slug from the checkout's GitHub remote (rename-proof); IRREVON_REPO
# overrides. Fails loudly outside a repo context — this script is owner-run only.
REPO="${IRREVON_REPO:-$(gh repo view --json nameWithOwner --jq .nameWithOwner)}"
RULESET_NAME="main-protection-phase1"
REQUIRED_CONTEXT="ci-required"

log()  { printf '\n== %s\n' "$*"; }
info() { printf '   %s\n' "$*"; }

api_get() { gh api "$@" 2>/dev/null; }

# ── phase 2: add ci-required as the ruleset's required status check ───────────
phase2() {
  log "PHASE 2 — require '$REQUIRED_CONTEXT' on the '$RULESET_NAME' ruleset"

  # Guard (docs/ci.md trap: a required check that never reported blocks the PR
  # forever): refuse unless a green ci-required check-run exists on a real PR.
  info "guard: looking for a successful pull_request run of ci.yml ..."
  local sha
  sha=$(api_get "repos/$REPO/actions/workflows/ci.yml/runs?event=pull_request&status=success&per_page=1" \
          --jq '.workflow_runs[0].head_sha // empty')
  if [ -z "$sha" ]; then
    echo "REFUSING: no successful pull_request run of ci.yml exists yet."
    echo "Merge-ready a PR until 'ci-required' reports green, then re-run --phase2."
    exit 1
  fi
  local green
  green=$(api_get "repos/$REPO/commits/$sha/check-runs?check_name=$REQUIRED_CONTEXT" \
            --jq '[.check_runs[] | select(.conclusion == "success")] | length')
  if [ "${green:-0}" -lt 1 ]; then
    echo "REFUSING: no green '$REQUIRED_CONTEXT' check-run found on $sha."
    exit 1
  fi
  info "guard OK: green '$REQUIRED_CONTEXT' check-run exists on $sha"

  local ruleset_id
  ruleset_id=$(api_get "repos/$REPO/rulesets" \
                 --jq ".[] | select(.name == \"$RULESET_NAME\") | .id")
  if [ -z "$ruleset_id" ]; then
    echo "REFUSING: ruleset '$RULESET_NAME' not found — run phase 1 first."
    exit 1
  fi

  local ruleset
  ruleset=$(api_get "repos/$REPO/rulesets/$ruleset_id")
  if printf '%s' "$ruleset" | jq -e \
       '.rules[] | select(.type == "required_status_checks")
        | .parameters.required_status_checks[]
        | select(.context == "'"$REQUIRED_CONTEXT"'")' >/dev/null; then
    info "already required: '$REQUIRED_CONTEXT' is on ruleset $ruleset_id - skip"
  else
    info "adding required_status_checks rule (single context '$REQUIRED_CONTEXT',"
    info "never individual jobs - docs/ci.md) to ruleset $ruleset_id ..."
    # PUT replaces the rules array: preserve the existing rules and append.
    printf '%s' "$ruleset" | jq '{rules: (.rules + [{
        type: "required_status_checks",
        parameters: {
          strict_required_status_checks_policy: false,
          do_not_enforce_on_create: false,
          required_status_checks: [{context: "'"$REQUIRED_CONTEXT"'"}]
        }
      }])}' \
      | gh api -X PUT "repos/$REPO/rulesets/$ruleset_id" --input - >/dev/null
    info "done"
  fi

  log "PHASE 2 VERIFICATION (read-back)"
  api_get "repos/$REPO/rulesets/$ruleset_id" \
    --jq '.rules[] | select(.type == "required_status_checks") | .parameters'
  echo
  echo "Phase 2 complete."
}

# ── phase 1: security + actions posture + ruleset ─────────────────────────────
phase1() {
  log "PHASE 1 — docs/ci.md owner checklist, items 1-5, for $REPO"

  # 1. Secret scanning + push protection + non-provider patterns.
  #    (Second layer only: local gitleaks stays the primary control.)
  log "1/6 secret scanning, push protection, non-provider patterns"
  local sa want_patch=0
  sa=$(api_get "repos/$REPO" --jq '.security_and_analysis')
  local k
  for k in secret_scanning secret_scanning_push_protection secret_scanning_non_provider_patterns; do
    local status
    status=$(printf '%s' "$sa" | jq -r ".${k}.status // \"disabled\"")
    if [ "$status" = "enabled" ]; then
      info "$k: already enabled - skip"
    else
      info "$k: $status -> enabling"
      want_patch=1
    fi
  done
  if [ "$want_patch" -eq 1 ]; then
    printf '%s' '{"security_and_analysis":{"secret_scanning":{"status":"enabled"},"secret_scanning_push_protection":{"status":"enabled"},"secret_scanning_non_provider_patterns":{"status":"enabled"}}}' \
      | gh api -X PATCH "repos/$REPO" --input - >/dev/null
    info "patched"
  fi

  # 2a. Dependabot alerts (GET returns 204 when enabled, 404 when disabled).
  log "2/6 Dependabot alerts"
  if api_get "repos/$REPO/vulnerability-alerts" >/dev/null; then
    info "already enabled - skip"
  else
    gh api -X PUT "repos/$REPO/vulnerability-alerts" >/dev/null
    info "enabled"
  fi

  # 2b. Automated security fixes (Dependabot security updates).
  log "3/6 automated security fixes"
  if [ "$(api_get "repos/$REPO/automated-security-fixes" --jq '.enabled')" = "true" ]; then
    info "already enabled - skip"
  else
    gh api -X PUT "repos/$REPO/automated-security-fixes" >/dev/null
    info "enabled"
  fi

  # 3a. Default workflow token permissions: read-only, no PR approval rights.
  log "4/6 Actions default workflow permissions"
  local wf
  wf=$(api_get "repos/$REPO/actions/permissions/workflow")
  if [ "$(printf '%s' "$wf" | jq -r '.default_workflow_permissions')" = "read" ] \
     && [ "$(printf '%s' "$wf" | jq -r '.can_approve_pull_request_reviews')" = "false" ]; then
    info "already read-only with PR-approval off - skip"
  else
    printf '%s' '{"default_workflow_permissions":"read","can_approve_pull_request_reviews":false}' \
      | gh api -X PUT "repos/$REPO/actions/permissions/workflow" --input - >/dev/null
    info "set to read-only, PR-approval off"
  fi

  # 3b. Fork-PR approval: ALL outside collaborators (the first-time-only default
  #     tier is gameable - docs/ci.md checklist item 3).
  log "5/6 fork-PR contributor approval policy"
  local policy
  policy=$(api_get "repos/$REPO/actions/permissions/fork-pr-contributor-approval" \
             --jq '.approval_policy // empty')
  if [ "$policy" = "all_external_contributors" ]; then
    info "already 'all_external_contributors' - skip"
  else
    info "'${policy:-unset}' -> 'all_external_contributors'"
    printf '%s' '{"approval_policy":"all_external_contributors"}' \
      | gh api -X PUT "repos/$REPO/actions/permissions/fork-pr-contributor-approval" --input - >/dev/null
    info "set"
  fi

  # 4. Ruleset phase 1 on the default branch: require PR (0 approvals — a solo
  #    owner cannot approve their own PR), block force pushes, restrict
  #    deletions. NO required status checks yet (phase 2, after ci-required has
  #    reported on a real PR — the never-reported/pending-forever trap).
  log "6/6 branch ruleset '$RULESET_NAME' (existence-check first)"
  local existing_id
  existing_id=$(api_get "repos/$REPO/rulesets" \
                  --jq ".[] | select(.name == \"$RULESET_NAME\") | .id")
  if [ -n "$existing_id" ]; then
    info "ruleset '$RULESET_NAME' already exists (id $existing_id) - skip"
  else
    printf '%s' '{
      "name": "'"$RULESET_NAME"'",
      "target": "branch",
      "enforcement": "active",
      "bypass_actors": [],
      "conditions": {"ref_name": {"include": ["~DEFAULT_BRANCH"], "exclude": []}},
      "rules": [
        {"type": "deletion"},
        {"type": "non_fast_forward"},
        {"type": "pull_request", "parameters": {
          "required_approving_review_count": 0,
          "dismiss_stale_reviews_on_push": false,
          "require_code_owner_review": false,
          "require_last_push_approval": false,
          "required_review_thread_resolution": false,
          "allowed_merge_methods": ["merge", "squash"]
        }}
      ]
    }' | gh api -X POST "repos/$REPO/rulesets" --input - >/dev/null
    info "created"
  fi

  # 5. nightly-failure label (used by the nightly dedup job — checklist item 5).
  log "extra: 'nightly-failure' label"
  if api_get "repos/$REPO/labels/nightly-failure" >/dev/null; then
    info "already exists - skip"
  else
    gh label create nightly-failure --repo "$REPO" \
      --description "Auto-filed by the nightly workflow on a red night" \
      --color B60205 >/dev/null
    info "created"
  fi

  # ── read-back verification ────────────────────────────────────────────────
  log "PHASE 1 VERIFICATION (read-back of every setting)"
  echo "security_and_analysis:"
  api_get "repos/$REPO" --jq '.security_and_analysis'
  echo "vulnerability-alerts enabled:"
  if api_get "repos/$REPO/vulnerability-alerts" >/dev/null; then echo true; else echo false; fi
  echo "automated-security-fixes:"
  api_get "repos/$REPO/automated-security-fixes"
  echo "actions workflow permissions:"
  api_get "repos/$REPO/actions/permissions/workflow"
  echo "fork-PR approval policy:"
  api_get "repos/$REPO/actions/permissions/fork-pr-contributor-approval"
  echo "ruleset '$RULESET_NAME':"
  local rid
  rid=$(api_get "repos/$REPO/rulesets" --jq ".[] | select(.name == \"$RULESET_NAME\") | .id")
  if [ -n "$rid" ]; then
    api_get "repos/$REPO/rulesets/$rid" \
      --jq '{name, enforcement, conditions, rules: [.rules[].type], bypass_actors}'
  else
    echo "MISSING"
  fi
  echo "nightly-failure label:"
  api_get "repos/$REPO/labels/nightly-failure" --jq '.name' || echo "MISSING"
  echo
  echo "Phase 1 complete. Manual UI items left (no full API): Actions allowlist +"
  echo "SHA-pin checkbox, CodeQL default setup, private vulnerability reporting"
  echo "(docs/ci.md checklist items 3, 7, 8)."
  echo "Run '--phase2' AFTER ci-required has reported green on a real PR."
}

if [ "${1:-}" = "--phase2" ]; then
  phase2
else
  phase1
fi
