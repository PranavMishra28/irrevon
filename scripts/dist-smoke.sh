#!/usr/bin/env bash
# Wheel-install smoke (N2 §5.3; make dist-smoke): prove the ADR-0018 no-Node
# guarantee chain end to end inside python:3.13-slim (no node binary), against
# the compose test Postgres on its private Docker network.
#
#   1. pip install the wheel into a clean venv
#   2. journey: init → doctor --json → demo --jsonl → serve --json → HTTP probes
#      (health incl. version header; effects incl. the flagship id; / is HTML
#      with no fixture sentinel) → SIGINT → exit 0
#   3. pip show -f audit: _web/index.html, _migrations/0005_read_role.sql,
#      _schemas/*.json packaged; irrevon --version == the single __version__
#   4. sdist leg: install the .tar.gz in a second venv, repeat the file audit
#
# Requires: `make dist` artifacts in dist/, docker, and the test Postgres from
# docker-compose.yml (`make py-db-up`). The smoke container joins that service's
# Docker network while Postgres remains bound to host loopback only.

set -euo pipefail
cd "$(dirname "$0")/.."

SMOKE_IMAGE="${IRREVON_SMOKE_IMAGE:-python:3.13-slim}"
SMOKE_DB_HOST="${IRREVON_SMOKE_DB_HOST:-ledger-db-test}"
SMOKE_DB_PORT="${IRREVON_SMOKE_DB_PORT:-5432}"

ls dist/irrevon-*.whl dist/irrevon-*.tar.gz >/dev/null || {
  echo "dist-smoke: no artifacts in dist/ — run \`make dist\` first" >&2
  exit 1
}

# Fail closed over the complete artifact surface, including ADR-0023's stale
# package-name guard. The sdist is a build input, not a repository snapshot.
echo "== artifact-content contract: sdist + wheel"
python3 scripts/check-dist-contents.py dist/irrevon-*.tar.gz dist/irrevon-*.whl

DB_CONTAINER=$(docker compose ps -q ledger-db-test)
if [ -z "$DB_CONTAINER" ]; then
  echo "dist-smoke: compose service ledger-db-test is not running" >&2
  exit 1
fi
SMOKE_NETWORK=$(docker inspect \
  --format '{{range $name, $_ := .NetworkSettings.Networks}}{{println $name}}{{end}}' \
  "$DB_CONTAINER" | sed -n '1p')
if [ -z "$SMOKE_NETWORK" ]; then
  echo "dist-smoke: could not resolve the compose network for ledger-db-test" >&2
  exit 1
fi

docker run --rm \
  --network "$SMOKE_NETWORK" \
  -e SMOKE_DSN="postgresql://postgres@${SMOKE_DB_HOST}:${SMOKE_DB_PORT}/irrevon_smoke" \
  -e ADMIN_DSN="postgresql://postgres@${SMOKE_DB_HOST}:${SMOKE_DB_PORT}/postgres" \
  -v "$PWD/dist":/dist:ro \
  -v "$PWD/scripts/dist-smoke-inner.sh":/smoke.sh:ro \
  "$SMOKE_IMAGE" \
  bash /smoke.sh

echo "dist-smoke: OK (wheel + sdist legs green in a Node-less container)"
