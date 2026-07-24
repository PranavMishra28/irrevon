#!/usr/bin/env bash
# Runs INSIDE python:3.13-slim (see dist-smoke.sh). No Node exists here — that
# absence is itself the first assertion.
set -euo pipefail

echo "== no-Node precondition"
if command -v node >/dev/null 2>&1; then
  echo "FAIL: node exists in the smoke container" >&2
  exit 1
fi

WHEEL=$(ls /dist/irrevon-*.whl)
SDIST=$(ls /dist/irrevon-*.tar.gz)
WORK=/tmp/smoke
mkdir -p "$WORK" && cd "$WORK"

echo "== wheel leg: clean venv install"
python -m venv venv-wheel
venv-wheel/bin/pip install --quiet "$WHEEL"
IRV=venv-wheel/bin/irrevon

echo "== journey: init"
"$IRV" init --dir . --json >init.json
python3 -c "import json; d=json.load(open('init.json')); assert sorted(d['written'])==['.env.example','compose.yaml','irrevon.toml'], d"

echo "== point the config at the smoke database"
venv-wheel/bin/python - <<'PY'
import os, psycopg
admin = os.environ["ADMIN_DSN"]
with psycopg.connect(admin, autocommit=True) as conn:
    conn.execute("DROP DATABASE IF EXISTS irrevon_smoke")
    conn.execute("CREATE DATABASE irrevon_smoke")
PY
cat >irrevon.toml <<EOF
schema_version = "1"

[ledger]
dsn = "${SMOKE_DSN}"

[demo]
seed = 42
EOF
# Migration authority is deliberately separate from the runtime config. Exercise
# that explicit boundary in the packaged-artifact journey.
IRREVON_MIGRATION_DSN="$SMOKE_DSN" \
  "$IRV" init --dir . --json >init2.json
python3 -c "import json; d=json.load(open('init2.json')); assert d['migrations_applied'], d"

echo "== journey: doctor --json (proves _migrations/_schemas/_web resolve from the wheel)"
"$IRV" doctor --json >doctor.json || { cat doctor.json; exit 1; }
python3 - <<'PY'
import json
d = json.load(open("doctor.json"))
assert d["ok"] is True, d
by = {c["name"]: c for c in d["checks"]}
for name in ("identity_selftest", "ledger_db", "capability_declarations", "serve_ready"):
    assert by[name]["status"] != "fail", by[name]
assert by["serve_ready"]["status"] == "ok", by["serve_ready"]  # wheel embeds _web
PY

echo "== journey: demo --jsonl (writes the artifact)"
IRREVON_MIGRATION_DSN="$ADMIN_DSN" \
  "$IRV" demo --jsonl --keep --artifact ./irrevon-demo-artifact.json >demo.jsonl
python3 - <<'PY'
import json
lines = [json.loads(l) for l in open("demo.jsonl") if l.strip()]
summary = lines[-1]
assert summary["contrast_holds"] is True, summary
assert summary["irrevon_leg"]["effect_id"] == (
    "0bb7e8d64711e0cc5ec277fb9bb64d3d321fdd53dd92b8ebb1752fde822785f5"
), summary
assert json.load(open("irrevon-demo-artifact.json"))["summary"]["contrast_holds"] is True
PY
DEMO_DSN=$(python3 -c "
import os
from urllib.parse import urlsplit
s = urlsplit(os.environ['SMOKE_DSN'])
print(s._replace(path='/irrevon_demo_s42').geturl())
")

echo "== journey: serve --json on an ephemeral port"
"$IRV" serve --json --port 0 --dsn "$DEMO_DSN" \
  --demo-artifact ./irrevon-demo-artifact.json --config ./irrevon.toml \
  >serve-ready.json 2>serve.log &
SERVE_PID=$!
for _ in $(seq 1 50); do [ -s serve-ready.json ] && break; sleep 0.2; done
[ -s serve-ready.json ] || { echo "FAIL: no serve ready line"; cat serve.log; exit 1; }
PORT=$(python3 -c "import json; print(json.load(open('serve-ready.json'))['port'])")

venv-wheel/bin/python - "$PORT" <<'PY'
import json, sys, urllib.request
port = sys.argv[1]
base = f"http://127.0.0.1:{port}"

with urllib.request.urlopen(f"{base}/api/v1/health", timeout=10) as resp:
    assert resp.status == 200
    assert resp.headers["Irrevon-Schema-Version"] == "1", dict(resp.headers)
    health = json.loads(resp.read())
    assert health["schema_version"] == "1" and health["ok"] is True, health

with urllib.request.urlopen(f"{base}/api/v1/effects", timeout=10) as resp:
    effects = json.loads(resp.read())
ids = [item["record"]["effect_id"] for item in effects["data"]]
flagship = "0bb7e8d64711e0cc5ec277fb9bb64d3d321fdd53dd92b8ebb1752fde822785f5"
assert flagship in ids, ids

with urllib.request.urlopen(f"{base}/", timeout=10) as resp:
    html = resp.read().decode()
    assert resp.headers["Content-Type"].startswith("text/html")
assert "<div id=\"root\">" in html or "<!doctype html>" in html.lower(), html[:200]
assert "Synthetic fixture" not in html  # no fixture sentinel in the live bundle
print("serve probes OK")
PY

# SIGTERM, not SIGINT: background children of a non-interactive shell ignore
# SIGINT; serve handles both identically (graceful close, exit 0).
kill -TERM "$SERVE_PID"
wait "$SERVE_PID" || { echo "FAIL: serve did not exit 0 on SIGTERM"; exit 1; }

echo "== journey: worker --max-cycles 2 (continuous service from the wheel)"
venv-wheel/bin/python -m irrevon.adapters.refdest_server --port 0 --seed 7 \
  >refdest-ready.txt 2>/dev/null &
REFDEST_PID=$!
for _ in $(seq 1 50); do grep -q "REFDEST READY" refdest-ready.txt 2>/dev/null && break; sleep 0.2; done
REFDEST_PORT=$(awk '{print $3}' refdest-ready.txt)
cat >>irrevon.toml <<EOF

[adapters.refdest-c2]
kind = "refdest"
EOF
IRREVON_REFDEST_URL="http://127.0.0.1:${REFDEST_PORT}" \
  "$IRV" worker --config ./irrevon.toml --dsn "$DEMO_DSN" \
  --interval 0.2 --sweep-interval 0.2 --max-cycles 2 \
  --health-file ./worker-health.json 2>worker.log \
  || { echo "FAIL: worker exited non-zero"; cat worker.log; exit 1; }
python3 - <<'PY'
import json
health = json.load(open("worker-health.json"))
assert health["cycle"] == 2, health
assert health["open_executions"] == 0, health  # demo DB is fully settled
PY
kill "$REFDEST_PID" 2>/dev/null || true

echo "== wheel file audit"
venv-wheel/bin/pip show -f irrevon >files.txt
grep -q "_web/index.html" files.txt
grep -q "_migrations/0005_read_role.sql" files.txt
grep -q "_schemas/effect-record.schema.json" files.txt
VERSION_CLI=$("$IRV" --version | awk '{print $2}')
VERSION_SRC=$(venv-wheel/bin/python -c "import irrevon; print(irrevon.__version__)")
[ "$VERSION_CLI" = "$VERSION_SRC" ] || { echo "FAIL: version drift"; exit 1; }

echo "== sdist leg: second clean venv (prebuilt assets, still no Node)"
python -m venv venv-sdist
venv-sdist/bin/pip install --quiet "$SDIST"
venv-sdist/bin/pip show -f irrevon >files-sdist.txt
grep -q "_web/index.html" files-sdist.txt
grep -q "_migrations/0005_read_role.sql" files-sdist.txt
grep -q "_schemas/effect-record.schema.json" files-sdist.txt
[ "$(venv-sdist/bin/irrevon --version | awk '{print $2}')" = "$VERSION_SRC" ]

echo "dist-smoke inner: all legs green"
