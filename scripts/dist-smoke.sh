#!/usr/bin/env bash
# Wheel-install smoke (N2 §5.3; make dist-smoke): prove the ADR-0018 no-Node
# guarantee chain end to end inside python:3.13-slim (no node binary), against
# the compose test Postgres on the host loopback.
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
# docker-compose.yml (`make py-db-up`). The container reaches the host DB via
# host.docker.internal (mapped with --add-host for Linux parity).

set -euo pipefail
cd "$(dirname "$0")/.."

SMOKE_IMAGE="${IRREVON_SMOKE_IMAGE:-python:3.13-slim}"
SMOKE_DB_HOST="${IRREVON_SMOKE_DB_HOST:-host.docker.internal}"
SMOKE_DB_PORT="${IRREVON_SMOKE_DB_PORT:-54329}"

ls dist/irrevon-*.whl dist/irrevon-*.tar.gz >/dev/null || {
  echo "dist-smoke: no artifacts in dist/ — run \`make dist\` first" >&2
  exit 1
}

# Stale-tree guard (ADR-0023): the pre-rename `detent` package must never ship.
# The sdist includes all of src/, so a resurrected legacy tree would ride along
# silently — assert both artifacts carry exactly one top-level package (irrevon)
# and zero `detent` path segments.
echo "== stale-tree guard: single-package audit of sdist + wheel"
python3 - dist/irrevon-*.tar.gz dist/irrevon-*.whl <<'PY'
import sys, tarfile, zipfile

sdist_path, wheel_path = sys.argv[1], sys.argv[2]

with tarfile.open(sdist_path) as tf:
    names = tf.getnames()
stale = [n for n in names if "detent" in {seg.lower() for seg in n.split("/")}]
assert not stale, f"sdist carries stale detent paths: {stale[:10]}"
src_pkgs = {n.split("/")[2] for n in names
            if len(n.split("/")) > 3 and n.split("/")[1] == "src"}
assert src_pkgs == {"irrevon"}, f"sdist src/ packages must be exactly {{'irrevon'}}: {src_pkgs}"

with zipfile.ZipFile(wheel_path) as zf:
    wnames = zf.namelist()
stale = [n for n in wnames if "detent" in {seg.lower() for seg in n.split("/")}]
assert not stale, f"wheel carries stale detent paths: {stale[:10]}"
top = {n.split("/")[0] for n in wnames if not n.split("/")[0].endswith(".dist-info")}
assert top == {"irrevon"}, f"wheel top-level packages must be exactly {{'irrevon'}}: {top}"

print(f"stale-tree guard OK: sdist src/ packages={sorted(src_pkgs)}, wheel top-level={sorted(top)}")
PY

docker run --rm \
  --add-host=host.docker.internal:host-gateway \
  -e SMOKE_DSN="postgresql://postgres@${SMOKE_DB_HOST}:${SMOKE_DB_PORT}/irrevon_smoke" \
  -e ADMIN_DSN="postgresql://postgres@${SMOKE_DB_HOST}:${SMOKE_DB_PORT}/postgres" \
  -v "$PWD/dist":/dist:ro \
  -v "$PWD/scripts/dist-smoke-inner.sh":/smoke.sh:ro \
  "$SMOKE_IMAGE" \
  bash /smoke.sh

echo "dist-smoke: OK (wheel + sdist legs green in a Node-less container)"
