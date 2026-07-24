#!/usr/bin/env bash
# Complete, non-publishing launch validation. Writes a machine-readable report.
set -euo pipefail

report=".scratch/launch-audit.json"
mkdir -p .scratch
started=$(date -u +"%Y-%m-%dT%H:%M:%SZ")
stage="startup"

finish() {
  code=$?
  finished=$(date -u +"%Y-%m-%dT%H:%M:%SZ")
  status="passed"
  if [ "$code" -ne 0 ]; then status="failed"; fi
  printf '%s\n' \
    "{" \
    "  \"schema_version\": \"1\"," \
    "  \"status\": \"$status\"," \
    "  \"last_stage\": \"$stage\"," \
    "  \"started_at\": \"$started\"," \
    "  \"finished_at\": \"$finished\"," \
    "  \"publishing_actions\": false" \
    "}" > "$report"
  echo "launch-audit: $status at $stage; report: $report"
  trap - EXIT
  exit "$code"
}
trap finish EXIT

stage="repository-gates"
make check dco

stage="python-unit-and-integration"
make py-check py-test py-test-integration

stage="workbench"
make web-check web-test web-e2e web-e2e-live

stage="marketing-site"
make site-check site-test site-vrt

stage="benchmark"
make bench-smoke

stage="package-clean-install"
make dist-smoke

stage="release-dry-run"
make release-dry-run

stage="public-data"
python3 scripts/check-public-data.py --include-generated
gitleaks dir --no-banner --redact site/dist
gitleaks dir --no-banner --redact dist
gitleaks dir --no-banner --redact src/irrevon/_web

stage="completed"
