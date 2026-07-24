"""Live-E2E foundation launcher (``make serve-live``): seed via a REAL
``irrevon demo`` run, then exec ``irrevon serve`` — the process WEB's
Playwright suite (the consolidator's ``web-e2e-live``) points at.

Invocation contract (documented in the Makefile serve-live block):

- env ``IRREVON_TEST_ADMIN_DSN`` — the test Postgres
  (default ``postgresql://postgres@127.0.0.1:54329/postgres``; ``make
  py-db-up`` starts it)
- env ``IRREVON_LIVE_ARTIFACT`` — demo artifact path
  (default ``/tmp/irrevon-demo-artifact.json``)
- env ``IRREVON_LIVE_PORT`` — serve port (default ``0`` = ephemeral)
- seeds seed 42 (``--keep``): kept demo DB ``irrevon_demo_s42``; deterministic
  flagship effect id
  ``0bb7e8d64711e0cc5ec277fb9bb64d3d321fdd53dd92b8ebb1752fde822785f5``
- stdout carries EXACTLY ONE line: serve's ``--json`` ready document
  ``{"schema_version": "1", "url": "http://127.0.0.1:<port>/", "port": …}``
  (demo output goes to stderr); stop with SIGINT/SIGTERM → exit 0.
"""

from __future__ import annotations

import os
import subprocess
import sys
import tempfile
from pathlib import Path

import psycopg

DEFAULT_ADMIN_DSN = "postgresql://postgres@127.0.0.1:54329/postgres"
SEED = 42


def main() -> int:
    admin_dsn = os.environ.get("IRREVON_TEST_ADMIN_DSN", DEFAULT_ADMIN_DSN)
    artifact = os.environ.get(
        "IRREVON_LIVE_ARTIFACT", "/tmp/irrevon-demo-artifact.json"
    )
    port = os.environ.get("IRREVON_LIVE_PORT", "0")

    with tempfile.TemporaryDirectory() as tmp:
        config_path = Path(tmp) / "irrevon.toml"
        config_path.write_text(
            f'schema_version = "1"\n\n[ledger]\ndsn = "{admin_dsn}"\n'
            f"\n[demo]\nseed = {SEED}\n",
            encoding="utf-8",
        )
        demo = subprocess.run(
            [
                sys.executable, "-m", "irrevon.cli", "demo",
                "--jsonl", "--keep", "--seed", str(SEED),
                "--artifact", artifact, "--config", str(config_path),
            ],
            env={**os.environ, "IRREVON_MIGRATION_DSN": admin_dsn},
            stdout=sys.stderr,  # stdout is reserved for the serve ready line
            timeout=300,
            check=False,
        )
        if demo.returncode != 0:
            print(f"serve-live: demo exited {demo.returncode}", file=sys.stderr)
            return demo.returncode

    demo_dsn = psycopg.conninfo.make_conninfo(
        admin_dsn, dbname=f"irrevon_demo_s{SEED}"
    )
    # Replace this process with serve: signals (SIGINT/SIGTERM) flow directly.
    os.execv(
        sys.executable,
        [
            sys.executable, "-m", "irrevon.cli", "serve",
            "--json", "--port", port,
            "--dsn", demo_dsn, "--demo-artifact", artifact,
        ],
    )


if __name__ == "__main__":
    sys.exit(main())
