#!/bin/bash
# Irrevon hard-deny hook for Cursor agents. Handles beforeShellExecution (input carries
# .command) and beforeReadFile (input carries .file_path). Only "deny" responses are
# reliably enforced by Cursor, so this script only allows or denies — it never asks.
# Honest limit: this file is repo-writable and regex-based; it is containment for a
# well-meaning-but-injected agent, not a security boundary (see docs/security-policy.md).
set -u
input=$(cat)

CANONICAL_REPO="PranavMishra28/irrevon"

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

matches() { printf '%s\n' "$cmd" | grep -qiE "$1"; }
api_method() {
  matches "(-X[[:space:]]*$1|-X$1|--method(=|[[:space:]])$1)([[:space:]]|$)"
}
launch_marker() {
  matches '(^|[[:space:]])IRREVON_V010_LAUNCH=1([[:space:]]|$)'
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
  matches '(-f|-F|--field|--raw-field)(=|[[:space:]])[^[:space:]]*(visibility|private|archived|name|owner)(=|%3D|\[)' &&
    return 1

  case "$cmd" in
    *"repos/${CANONICAL_REPO}/rulesets/"*)
      matches "repos/${CANONICAL_REPO}/rulesets/[0-9]+([[:space:]]|$)" &&
        api_method PUT ;;
    *"repos/${CANONICAL_REPO}/actions/permissions/selected-actions"*)
      matches "repos/${CANONICAL_REPO}/actions/permissions/selected-actions([[:space:]]|$)" &&
        api_method PUT ;;
    *"repos/${CANONICAL_REPO}/actions/permissions"*)
      matches "repos/${CANONICAL_REPO}/actions/permissions([[:space:]]|$)" &&
        api_method PUT ;;
    *"repos/${CANONICAL_REPO}/private-vulnerability-reporting"*)
      matches "repos/${CANONICAL_REPO}/private-vulnerability-reporting([[:space:]]|$)" &&
        api_method PUT ;;
    *"repos/${CANONICAL_REPO}/automated-security-fixes"*)
      matches "repos/${CANONICAL_REPO}/automated-security-fixes([[:space:]]|$)" &&
        api_method PUT ;;
    *"repos/${CANONICAL_REPO}/vulnerability-alerts"*)
      matches "repos/${CANONICAL_REPO}/vulnerability-alerts([[:space:]]|$)" &&
        api_method PUT ;;
    *"repos/${CANONICAL_REPO}/immutable-releases"*)
      matches "repos/${CANONICAL_REPO}/immutable-releases([[:space:]]|$)" &&
        api_method PUT ;;
    *"repos/${CANONICAL_REPO}/environments/release"*)
      matches "repos/${CANONICAL_REPO}/environments/release([[:space:]]|$)" &&
        { api_method PUT || api_method PATCH; } ;;
    *"repos/${CANONICAL_REPO}/actions/runs/"*"/pending_deployments"*)
      matches "repos/${CANONICAL_REPO}/actions/runs/[0-9]+/pending_deployments([[:space:]]|$)" &&
        api_method POST ;;
    *"repos/${CANONICAL_REPO}/discussions/categories"*)
      matches "repos/${CANONICAL_REPO}/discussions/categories(/[0-9]+)?([[:space:]]|$)" &&
        { api_method POST || api_method PATCH; } ;;
    *"repos/${CANONICAL_REPO}/discussions"*)
      matches "repos/${CANONICAL_REPO}/discussions(/[0-9]+)?([[:space:]]|$)" &&
        { api_method POST || api_method PATCH; } ;;
    *"repos/${CANONICAL_REPO}"*)
      matches "repos/${CANONICAL_REPO}([[:space:]]|$)" &&
        api_method PATCH &&
        matches '(has_discussions|security_and_analysis)' ;;
    *)
      return 1 ;;
  esac
}

# Git history / force push
matches 'push[^|;&]*(--force([[:space:]=]|$)|-f([[:space:]]|$)|--force-with-lease([[:space:]=]|$))' \
  && deny "Force push is blocked. Human-only operation."
matches 'git[[:space:]]+(filter-branch|filter-repo)|reflog[[:space:]]+expire' \
  && deny "Git history rewriting is blocked. Human-only operation."

# Tags are limited to the one owner-ratified software release. Listing and
# verification commands remain read-only and are not restricted here.
if matches '(^|[[:space:]])git[[:space:]]+tag[[:space:]]'; then
  if matches 'git[[:space:]]+tag[[:space:]]+(--list|-l|--verify|-v)([[:space:]]|$)'; then
    :
  elif launch_marker &&
    matches 'git[[:space:]]+tag[[:space:]]+(-a|--annotate)[[:space:]]+v0[.]1[.]0([[:space:]]|$)' &&
    ! matches '[;&|`]|[$][(]|(^|[[:space:]])(>|<)'; then
    :
  else
    deny "Only the marked, annotated v0.1.0 launch tag is authorized."
  fi
fi
if matches 'git[[:space:]]+push[^|;&]*((refs/tags/)?v[0-9]+[.][0-9]+[.][0-9]+)'; then
  if launch_marker &&
    matches 'refs/tags/v0[.]1[.]0([:[:space:]]|$)' &&
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

# gh api uses POST implicitly when fields or --input are supplied. Treat every
# non-GET method and every implicit-data invocation as a mutation; allow only
# the exact launch endpoints above. GraphQL mutations remain denied because
# their target cannot be proved from the command line alone.
if matches 'gh[[:space:]]+api([[:space:]]|$)'; then
  if matches 'gh[[:space:]]+api[[:space:]]+graphql([[:space:]]|$)'; then
    if matches '(^|[^[:alnum:]_])mutation([^[:alnum:]_]|$)|(^|[[:space:]])--input(=|[[:space:]])'; then
      deny "GraphQL mutations and file-sourced GraphQL requests are outside the launch allowlist."
    fi
    allow
  elif api_method GET; then
    :
  elif api_method POST || api_method PATCH || api_method PUT || api_method DELETE ||
    matches '(^|[[:space:]])(-f|-F|--field|--raw-field|--input)(=|[[:space:]])'; then
    scoped_launch_api_mutation ||
      deny "GitHub API mutation is outside the canonical v0.1.0 launch allowlist."
  fi
fi

# Local Vercel mutation commands cannot prove the configured project identity.
# The launch authorization uses the scoped Vercel connector instead.
matches '(^|[[:space:]])(vercel|vc)[[:space:]]+(deploy|promote|rollback|remove|alias|env|project|domains|certs|dns)([[:space:]]|$)' \
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
