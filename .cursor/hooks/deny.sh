#!/bin/bash
# Irrevon hard-deny hook for Cursor agents. Handles beforeShellExecution (input carries
# .command) and beforeReadFile (input carries .file_path). Only "deny" responses are
# reliably enforced by Cursor, so this script only allows or denies — it never asks.
# Honest limit: this file is repo-writable and regex-based; it is containment for a
# well-meaning-but-injected agent, not a security boundary (see docs/security-policy.md).
set -u
input=$(cat)

CANONICAL_REPO="PranavMishra28/irrevon"
MAIN_RULESET_ID="19426315"
WELCOME_REPOSITORY_ID="R_kgDOTeu25A"
WELCOME_CATEGORY_ID="DIC_kwDOTeu25M4DB51i"
WELCOME_PAYLOAD="/tmp/irrevon-v010-welcome-discussion.json"
WELCOME_TITLE="Welcome to the Irrevon community"
WELCOME_BODY="Use Discussions for questions, ideas, design feedback, integrations, experiments, and advice. Use Issues for reproducible bugs, documentation defects, benchmark-integrity concerns, and scoped work. Pull requests are for implementations. Report security vulnerabilities privately through GitHub Private Vulnerability Reporting. This community has no support SLA; participation is governed by the Code of Conduct. Never post credentials, private payloads, benchmark holdouts, or personal data."
WELCOME_QUERY='mutation CreateDiscussion($repositoryId: ID!, $categoryId: ID!, $title: String!, $body: String!) { createDiscussion(input: {repositoryId: $repositoryId, categoryId: $categoryId, title: $title, body: $body}) { discussion { url } } }'

# jq may not be on the hook's PATH; fall back to common locations, then to sed.
JQ=""
for c in jq /opt/homebrew/bin/jq /usr/local/bin/jq /usr/bin/jq; do
  if command -v "$c" >/dev/null 2>&1; then JQ="$c"; break; fi
done

json_field() {
  if [ -n "$JQ" ]; then
    printf '%s' "$input" | "$JQ" -r --arg k "$1" '.[$k] // empty' 2>/dev/null
  else
    printf '%s' "$input" | sed -n 's/.*"'"$1"'"[[:space:]]*:[[:space:]]*"\([^"]*\)".*/\1/p' | head -n 1
  fi
}

# Responses are fixed strings (no quotes/backslashes), safe to emit without jq.
deny() {
  printf '{"continue": true, "permission": "deny", "user_message": "%s", "agent_message": "%s"}\n' "$1" "$1"
  exit 0
}
allow() {
  printf '{"continue": true, "permission": "allow"}\n'
  exit 0
}

# ── beforeReadFile: block credential-file reads ───────────────────────────────
path=$(json_field file_path)
[ -z "$path" ] && path=$(json_field path)
if [ -n "$path" ]; then
  case "$path" in
    *.env|*.env.*|*/.env|*/.env.*|*/.ssh/*|*/.aws/*|*/.config/gh/*|*.pem|*.key|*id_rsa*|*id_ed25519*|*/.netrc|*/.pypirc|*.tripwords)
      deny "Reading credential or local-only files is blocked by policy." ;;
  esac
  allow
fi

# ── beforeShellExecution: block one-way-door commands ─────────────────────────
cmd=$(json_field command)
[ -z "$cmd" ] && allow
case "$cmd" in
  *$'\n'*|*$'\r'*)
    deny "Multiline shell commands are blocked by policy." ;;
esac

matches() { printf '%s\n' "$cmd" | grep -qiE "$1"; }
api_method() {
  matches "(-X[[:space:]]*$1|-X$1|--method(=|[[:space:]])$1)([[:space:]]|$)"
}
launch_marker() {
  matches '(^|[[:space:]])IRREVON_V010_LAUNCH=1([[:space:]]|$)'
}
exact_input() {
  matches "(^|[[:space:]])--input(=|[[:space:]])$1([[:space:]]|$)"
}

# The owner-authorized v0.1.0 launch is deliberately narrower than a general
# administrative bypass. Mutating GitHub API commands must be one command (no
# chaining or shell indirection), name the canonical repository in the REST
# endpoint, and target one of the launch surfaces ratified in AGENTS.md.
scoped_launch_api_mutation() {
  launch_marker || return 1
  matches '[;&|`]|[$][(]|(^|[[:space:]])(>|<)' && return 1
  matches "repos/${CANONICAL_REPO}" || return 1
  other_repos=${cmd//repos\/$CANONICAL_REPO/}
  printf '%s\n' "$other_repos" | grep -q 'repos/' && return 1
  input_count=$(printf '%s\n' "$cmd" |
    grep -oE '(^|[[:space:]])--input(=|[[:space:]])' |
    wc -l |
    tr -d '[:space:]')
  [ "$input_count" -gt 1 ] && return 1
  matches '(^|[[:space:]])(-f|-F|--field|--raw-field)(=|[[:space:]])@' &&
    return 1
  matches '(^|[[:space:]])(-f|-F|--field|--raw-field)(=|[[:space:]])[^[:space:]]*=@' &&
    return 1
  matches '(-f|-F|--field|--raw-field)(=|[[:space:]])[^[:space:]]*(visibility|private|archived|name|owner|has_issues|has_projects|has_wiki|default_branch|allow_[^=]*|delete_branch_on_merge)(=|%3D|\[)' &&
    return 1

  case "$cmd" in
    *"repos/${CANONICAL_REPO}/rulesets/"*)
      matches "repos/${CANONICAL_REPO}/rulesets/${MAIN_RULESET_ID}([[:space:]]|$)" &&
        api_method PUT &&
        exact_input '/tmp/irrevon-v010-ruleset[.]json' ;;
    *"repos/${CANONICAL_REPO}/actions/permissions/selected-actions"*)
      matches "repos/${CANONICAL_REPO}/actions/permissions/selected-actions([[:space:]]|$)" &&
        api_method PUT &&
        exact_input '/tmp/irrevon-v010-selected-actions[.]json' ;;
    *"repos/${CANONICAL_REPO}/actions/permissions"*)
      matches "repos/${CANONICAL_REPO}/actions/permissions([[:space:]]|$)" &&
        api_method PUT &&
        exact_input '/tmp/irrevon-v010-actions-permissions[.]json' ;;
    *"repos/${CANONICAL_REPO}/immutable-releases"*)
      matches "repos/${CANONICAL_REPO}/immutable-releases([[:space:]]|$)" &&
        api_method PUT ;;
    *"repos/${CANONICAL_REPO}/environments/release"*)
      matches "repos/${CANONICAL_REPO}/environments/release([[:space:]]|$)" &&
        { api_method PUT || api_method PATCH; } &&
        exact_input '/tmp/irrevon-v010-release-environment[.]json' ;;
    *"repos/${CANONICAL_REPO}/actions/runs/"*"/pending_deployments"*)
      release_run_id=$(printf '%s\n' "$cmd" |
        sed -n 's/.*IRREVON_RELEASE_RUN_ID=\([0-9][0-9]*\).*/\1/p')
      [ -n "$release_run_id" ] &&
        matches "repos/${CANONICAL_REPO}/actions/runs/${release_run_id}/pending_deployments([[:space:]]|$)" &&
        api_method POST &&
        exact_input '/tmp/irrevon-v010-deployment-review[.]json' ;;
    *"repos/${CANONICAL_REPO}/discussions/categories"*)
      matches "repos/${CANONICAL_REPO}/discussions/categories(/[0-9]+)?([[:space:]]|$)" &&
        ! matches '(^|[[:space:]])--input(=|[[:space:]])' &&
        { api_method POST || api_method PATCH; } ;;
    *"repos/${CANONICAL_REPO}/discussions"*)
      matches "repos/${CANONICAL_REPO}/discussions(/[0-9]+)?([[:space:]]|$)" &&
        ! matches '(^|[[:space:]])--input(=|[[:space:]])' &&
        { api_method POST || api_method PATCH; } ;;
    *"repos/${CANONICAL_REPO}"*)
      if matches "^IRREVON_V010_LAUNCH=1 gh api (-X[[:space:]]*PATCH|--method(=|[[:space:]])PATCH) repos/${CANONICAL_REPO} -f has_discussions=true[[:space:]]*$"; then
        :
      elif matches "^IRREVON_V010_LAUNCH=1 gh api (-X[[:space:]]*PATCH|--method(=|[[:space:]])PATCH) repos/${CANONICAL_REPO} -f security_and_analysis\\[(secret_scanning_non_provider_patterns|secret_scanning_validity_checks)\\]\\[status\\]=enabled[[:space:]]*$"; then
        :
      else
        return 1
      fi ;;
    *)
      return 1 ;;
  esac
}

# GitHub exposes Discussion creation only through GraphQL. Permit one immutable
# launch payload after proving its repository, category, copy, operation, and
# complete key set with jq. Any missing tool, unreadable file, or extra field
# fails closed.
scoped_welcome_discussion_mutation() {
  launch_marker || return 1
  [ -n "$JQ" ] || return 1
  [ -r "$WELCOME_PAYLOAD" ] || return 1
  matches "^IRREVON_V010_LAUNCH=1 gh api graphql --input ${WELCOME_PAYLOAD}[[:space:]]*$" ||
    return 1
  "$JQ" -e \
    --arg query "$WELCOME_QUERY" \
    --arg repository_id "$WELCOME_REPOSITORY_ID" \
    --arg category_id "$WELCOME_CATEGORY_ID" \
    --arg title "$WELCOME_TITLE" \
    --arg body "$WELCOME_BODY" \
    '
      type == "object" and
      keys == ["query", "variables"] and
      .query == $query and
      (.variables | type == "object") and
      (.variables | keys == ["body", "categoryId", "repositoryId", "title"]) and
      .variables.repositoryId == $repository_id and
      .variables.categoryId == $category_id and
      .variables.title == $title and
      .variables.body == $body
    ' "$WELCOME_PAYLOAD" >/dev/null 2>&1
}

# Git history / force push
matches 'push[^|;&]*(--force([[:space:]=]|$)|-f([[:space:]]|$)|--force-with-lease([[:space:]=]|$))' \
  && deny "Force push is blocked. Human-only operation."
matches 'git[[:space:]]+push[^|;&]*[[:space:]][+][^[:space:]]+' \
  && deny "Force push refspecs are blocked. Human-only operation."
matches 'git[[:space:]]+(filter-branch|filter-repo)|reflog[[:space:]]+expire' \
  && deny "Git history rewriting is blocked. Human-only operation."
matches 'git[[:space:]]+push[^|;&]*[[:space:]](--delete|-d)([[:space:]]|$)' \
  && deny "Deleting remote refs is blocked. Human-only operation."
matches 'git[[:space:]]+push[^|;&]*[[:space:]]:[^[:space:]]+' \
  && deny "Deleting remote refs is blocked. Human-only operation."
matches 'git[[:space:]]+push[^|;&]*[[:space:]]([^[:space:]]+:)?(refs/heads/)?main([[:space:]]|$)' \
  && deny "Direct source pushes to main are blocked; use the protected pull-request path."

# Tags are limited to the one owner-ratified software release. Listing and
# verification commands remain read-only and are not restricted here.
if matches '(^|[[:space:]])git[[:space:]]+tag[[:space:]]'; then
  if matches 'git[[:space:]]+tag[[:space:]]+(--list|-l|--verify|-v)([[:space:]]|$)'; then
    :
  elif launch_marker &&
    matches 'git[[:space:]]+tag[[:space:]]+(-a|--annotate)[[:space:]]+v0[.]1[.]0[[:space:]]+origin/main[[:space:]]+(-m|--message)(=|[[:space:]]).+' &&
    ! matches '[;&|`]|[$][(]|(^|[[:space:]])(>|<)'; then
    :
  else
    deny "Only the marked, annotated v0.1.0 launch tag is authorized."
  fi
fi
if matches 'git[[:space:]]+push[^|;&]*((refs/tags/)?v[0-9]+[.][0-9]+[.][0-9]+)'; then
  if launch_marker &&
    matches 'git[[:space:]]+push[[:space:]]+origin[[:space:]]+refs/tags/v0[.]1[.]0[[:space:]]*$' &&
    ! matches '[;&|`]|[$][(]|(^|[[:space:]])(>|<)'; then
    :
  else
    deny "Only the marked v0.1.0 launch tag may be pushed."
  fi
fi

# Repo settings / visibility / secrets / releases. Read-only API commands remain
# allowed; direct release commands stay workflow-only.
matches 'gh[[:space:]]+repo[[:space:]]+(edit|delete|transfer|archive|rename)' \
  && deny "Repository settings/visibility changes are blocked. Human-only operation."
matches 'gh[[:space:]]+secret' \
  && deny "GitHub secrets are blocked. Human-only operation."
matches 'gh[[:space:]]+release' \
  && deny "Direct GitHub Release commands are blocked; the protected release workflow owns v0.1.0."
matches 'gh[[:space:]]+pr[[:space:]]+merge[^|;&]*--admin(=|[[:space:]]|$)' \
  && deny "Administrative pull-request merges are blocked; required checks must pass normally."

# gh api uses POST implicitly when fields or --input are supplied. Treat every
# non-GET method and every implicit-data invocation as a mutation; allow only
# the exact launch endpoints above. GraphQL mutations remain denied except for
# the jq-validated, immutable welcome-Discussion payload.
if matches 'gh[[:space:]]+api([[:space:]]|$)'; then
  if matches 'gh[[:space:]]+api[[:space:]]+graphql([[:space:]]|$)'; then
    if matches '(^|[^[:alnum:]_])mutation([^[:alnum:]_]|$)|(^|[[:space:]])--input(=|[[:space:]])'; then
      scoped_welcome_discussion_mutation ||
        deny "GraphQL mutation is outside the exact welcome-Discussion launch allowlist."
    fi
    allow
  elif api_method GET; then
    :
  elif matches '(^|[[:space:]])(-X|--method)(=|[[:space:]]*)[[:alpha:]]+' ||
    matches '(^|[[:space:]])(-f|-F|--field|--raw-field|--input)(=|[[:space:]])'; then
    scoped_launch_api_mutation ||
      deny "GitHub API mutation is outside the canonical v0.1.0 launch allowlist."
  fi
fi

# Local Vercel mutation commands cannot prove the configured project identity.
# The launch authorization uses the scoped Vercel connector instead.
matches '(^|[[:space:]])([^[:space:]]*/)?(vercel|vc)([[:space:]]|$)' \
  && deny "Vercel mutations must use the configured, project-scoped connector."

# Publishing
matches '(npm|pnpm|yarn)[[:space:]]+publish|twine[[:space:]]+upload|uv[[:space:]]+publish|cargo[[:space:]]+publish' \
  && deny "Package publishing is blocked. Human-only operation."

# Hook / scanner bypass
matches '(--no-verify|SKIP=gitleaks)' \
  && deny "Bypassing pre-commit hooks or the secret scan is blocked."

# Destructive deletes outside the workspace
matches 'rm[[:space:]]+-[a-zA-Z]*[rf][a-zA-Z]*[[:space:]]+("?/|~|\$HOME)' \
  && deny "Recursive delete outside the workspace is blocked."

# Data exfiltration via network tools
matches '(curl|wget)[^|;&]*(--data|--upload-file|[[:space:]]-d[[:space:]]|[[:space:]]-F[[:space:]]|[[:space:]]-T[[:space:]])' \
  && deny "Uploading data with curl/wget is blocked."
matches '(^|[[:space:]&|;])(nc|ncat|scp|sftp)([[:space:]]|$)' \
  && deny "Raw network transfer tools are blocked."

# Credential-file reads via shell
matches '(cat|less|head|tail|grep|strings|base64|xxd)[[:space:]][^|;&]*(\.env([[:space:]./]|$)|\.ssh/|\.aws/|\.config/gh|hosts\.yml|\.netrc|\.pypirc|\.tripwords)' \
  && deny "Reading credential or local-only files is blocked by policy."

allow
