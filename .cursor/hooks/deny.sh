#!/bin/bash
# Detent hard-deny hook for Cursor agents. Handles beforeShellExecution (input carries
# .command) and beforeReadFile (input carries .file_path). Only "deny" responses are
# reliably enforced by Cursor, so this script only allows or denies — it never asks.
# Honest limit: this file is repo-writable and regex-based; it is containment for a
# well-meaning-but-injected agent, not a security boundary (see docs/security-policy.md).
set -u
input=$(cat)

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
    *.env|*.env.*|*/.env|*/.env.*|*/.ssh/*|*/.aws/*|*/.config/gh/*|*.pem|*.key|*id_rsa*|*id_ed25519*|*/.netrc|*.tripwords)
      deny "Reading credential or local-only files is blocked by policy." ;;
  esac
  allow
fi

# ── beforeShellExecution: block one-way-door commands ─────────────────────────
cmd=$(json_field command)
[ -z "$cmd" ] && allow

matches() { printf '%s\n' "$cmd" | grep -qE "$1"; }

# Git history / force push
matches 'push[^|;&]*(--force|-f[[:space:]]|--force-with-lease)' \
  && deny "Force push is blocked. Human-only operation."
matches 'git[[:space:]]+(filter-branch|filter-repo)|reflog[[:space:]]+expire' \
  && deny "Git history rewriting is blocked. Human-only operation."

# Repo settings / visibility / secrets / releases
matches 'gh[[:space:]]+repo[[:space:]]+(edit|delete|transfer|archive|rename)' \
  && deny "Repository settings/visibility changes are blocked. Human-only operation."
matches 'gh[[:space:]]+(secret|release)' \
  && deny "GitHub secrets and releases are blocked. Human-only operation."
matches 'gh[[:space:]]+api[^|;&]*(-X|--method)[[:space:]]+(PATCH|PUT|DELETE)' \
  && deny "Mutating GitHub API calls are blocked. Human-only operation."

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
