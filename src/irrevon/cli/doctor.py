"""``irrevon doctor`` — read-only environment validation (RFC-002 §12).

Never mutates, never dispatches; ``--probe`` opts into declared read-only
liveness calls. Checks, in order: config · identity self-test against pinned
vectors · DB reachability/migrations/privileges · declaration validation ·
credential PRESENCE only (values never printed) · clock sanity.
Exit codes: 0 all pass · 3 one or more fail · 1 doctor crashed · 2 usage.
"""

from __future__ import annotations

import hashlib
import json
import os
from dataclasses import dataclass
from typing import Any

from irrevon.adapters.base import declarations_dir, load_declaration
from irrevon.cli.config import Config
from irrevon.identity import canonical_bytes, derive_intent_id

# Pinned identity vectors — the cross-implementation digests from the T-000
# spike (ADR-0020; tests/identity/vectors/ carries the full committed set).
# Doctor re-proves the canonicalization on EVERY machine: this is the
# invariant the whole project rests on (master doc §7.2).
_PINNED_VECTORS: list[tuple[dict[str, Any], str]] = [
    (
        {
            "stable_ids": {"order_id": "9410", "customer_ref": "C-0007"},
            "effect_type": "order.create",
            "scope": "acme-store/prod",
        },
        "0bb7e8d64711e0cc5ec277fb9bb64d3d321fdd53dd92b8ebb1752fde822785f5",
    ),
    (
        {
            "numbers": [333333333.33333329, 1e30, 4.50, 2e-3, 1e-27],
            "string": "\u20ac$\u000f\u000aA'\u0042\u0022\u005c\\\"\u002f",
            "literals": [None, True, False],
        },
        "2d5e01a318d0f0879ab568c4be289c8b1f64ef8921a53c6277d5e069978baacb",
    ),
]


@dataclass(slots=True)
class CheckResult:
    name: str
    status: str  # ok | warn | fail
    message: str
    hint: str | None = None


def _check_config(config: Config) -> CheckResult:
    if config.path is None:
        return CheckResult(
            "config",
            "warn",
            "no irrevon.toml found; using built-in defaults",
            "run `irrevon init`",
        )
    return CheckResult("config", "ok", f"loaded {config.path}")


def _check_identity() -> CheckResult:
    for value, expected in _PINNED_VECTORS:
        actual = hashlib.sha256(canonical_bytes(value)).hexdigest()
        if actual != expected:
            return CheckResult(
                "identity_selftest",
                "fail",
                "JCS+SHA-256 does not reproduce the pinned conformance vectors",
                "the canonicalization is non-conformant — do not run anything; "
                "report this (T-101 human-review trigger)",
            )
    derived = derive_intent_id(
        {"order_id": "9410", "customer_ref": "C-0007"},
        "order.create",
        "acme-store/prod",
    )
    if derived != _PINNED_VECTORS[0][1]:
        return CheckResult(
            "identity_selftest", "fail", "intent_id derivation drifted", None
        )
    return CheckResult(
        "identity_selftest", "ok", "pinned vectors reproduce byte-for-byte"
    )


def _check_ledger(config: Config, *, read_only: bool = False) -> list[CheckResult]:
    import psycopg

    from irrevon.ledger.db import migrations_dir

    results: list[CheckResult] = []
    try:
        if read_only:
            # Serve context: connect as the SELECT-only irrevon_read role with
            # the session forced read-only — the health path must never open a
            # write-capable connection (read_dsn sets connect_timeout=5).
            from irrevon.serve import read_dsn

            conn = psycopg.connect(read_dsn(config.resolved_dsn()))
        else:
            conn = psycopg.connect(config.resolved_dsn(), connect_timeout=5)
    except psycopg.OperationalError as err:
        # A missing role/database on a reachable server is the signature of a
        # database created before the Irrevon rename (ADR-0023).
        hint = "docker compose up -d --wait && irrevon doctor"
        if 'role "irrevon' in str(err) or 'database "irrevon' in str(err):
            hint = (
                "stale pre-rename database? recreate it: "
                "docker compose down -v && docker compose up -d --wait "
                "&& irrevon init"
            )
        return [
            CheckResult(
                "ledger_db",
                "fail",
                f"Postgres unreachable: {err}",
                hint,
            )
        ]
    with conn:
        applied = set()
        legacy_journal = False
        try:
            applied = {
                r[0]
                for r in conn.execute(
                    "SELECT filename FROM irrevon_schema_migrations"
                ).fetchall()
            }
        except psycopg.errors.UndefinedTable:
            conn.rollback()
            row = conn.execute(
                "SELECT to_regclass('detent_schema_migrations')"
            ).fetchone()
            legacy_journal = row is not None and row[0] is not None
        expected = {p.name for p in migrations_dir().glob("*.sql")}
        missing = sorted(expected - applied)
        if missing:
            if legacy_journal:
                results.append(
                    CheckResult(
                        "ledger_db",
                        "fail",
                        "stale pre-rename database (a detent_schema_migrations "
                        "journal exists; ADR-0023 renamed the roles and journal)",
                        "recreate it: docker compose down -v && "
                        "docker compose up -d --wait && irrevon init",
                    )
                )
            else:
                results.append(
                    CheckResult(
                        "ledger_db",
                        "fail",
                        f"migrations not applied: {missing}",
                        "docker compose up -d --wait && irrevon init (applies them)",
                    )
                )
        else:
            triggers = conn.execute(
                "SELECT count(*) FROM pg_trigger WHERE tgname LIKE '%_append_only'"
            ).fetchone()
            if triggers is None or triggers[0] == 0:
                results.append(
                    CheckResult(
                        "ledger_db", "fail", "append-only triggers missing", None
                    )
                )
            else:
                results.append(
                    CheckResult(
                        "ledger_db",
                        "ok",
                        f"reachable; {len(applied)} migrations; "
                        f"{triggers[0]} append-only triggers",
                    )
                )
        # ledger_write: round-trip inside a transaction that is ROLLED BACK —
        # doctor never mutates (RFC-002 §12). In the read-only serve context
        # the probe is skipped, honestly: the health surface runs as
        # irrevon_read and must not exercise a write path at all.
        if read_only:
            results.append(
                CheckResult(
                    "ledger_write",
                    "skipped",
                    "not probed (read-only serve context)",
                    "run `irrevon doctor` as the operator for the write probe",
                )
            )
        else:
            try:
                with conn.transaction() as _txn:
                    conn.execute("CREATE TEMPORARY TABLE irrevon_doctor_probe (x int)")
                    conn.execute("INSERT INTO irrevon_doctor_probe VALUES (1)")
                    row = conn.execute("SELECT x FROM irrevon_doctor_probe").fetchone()
                    assert row is not None and row[0] == 1
                    raise _Rollback()
            except _Rollback:
                results.append(
                    CheckResult("ledger_write", "ok", "write round-trip OK (rolled back)")
                )
            except psycopg.Error as err:
                results.append(
                    CheckResult("ledger_write", "fail", f"write probe failed: {err}", None)
                )
        # clock sanity: authority freshness depends on DB-vs-local skew.
        row = conn.execute(
            "SELECT abs(EXTRACT(EPOCH FROM (now() - %s::timestamptz))) AS skew",
            (_now_iso(),),
        ).fetchone()
        skew = float(row[0]) if row else 0.0
        if skew > 30:
            results.append(
                CheckResult(
                    "clock", "fail", f"local vs DB clock skew {skew:.1f}s", "check NTP"
                )
            )
        else:
            results.append(CheckResult("clock", "ok", f"skew {skew:.1f}s"))
    return results


class _Rollback(Exception):
    pass


def _now_iso() -> str:
    from datetime import UTC, datetime

    return datetime.now(UTC).isoformat()


def _check_declarations(config: Config) -> CheckResult:
    try:
        names = []
        for path in sorted(declarations_dir().glob("*.capability.json")):
            declaration = load_declaration(path)
            if not declaration["citations"]:
                return CheckResult(
                    "capability_declarations", "fail",
                    f"{path.name}: citations empty", None,
                )
            names.append(declaration["adapter"])
        return CheckResult(
            "capability_declarations", "ok", f"valid: {', '.join(names)}"
        )
    except ValueError as err:
        return CheckResult("capability_declarations", "fail", str(err), None)


def _check_credentials(config: Config) -> CheckResult:
    missing = []
    for name, entry in config.adapters.items():
        env_name = entry.get("credentials")
        if env_name and not os.environ.get(str(env_name)):
            missing.append(f"{name}: {env_name}")
    if config.password_env and not os.environ.get(config.password_env):
        return CheckResult(
            "credentials",
            "warn",
            f"env var {config.password_env} not set (fine for trust-auth local DBs)",
            f"set {config.password_env} in .env",
        )
    if missing:
        return CheckResult(
            "credentials", "fail", f"missing env vars: {missing}",
            "names only are checked; values are never printed",
        )
    return CheckResult("credentials", "ok", "all named env vars present")


def _check_serve_ready(config: Config) -> CheckResult:
    """Serve-readiness (after ``credentials``): (a) workbench assets present in
    the installed package — ``warn`` if absent, API-only serve still works;
    (b) the ``irrevon_read`` role exists and a ``SELECT 1`` under
    ``default_transaction_read_only=on`` succeeds — ``fail`` with the
    migrations hint (0005 ships the role). Port availability is deliberately
    NOT checked (races; serve's preflight owns it). Read-only, as all checks.
    """
    import psycopg

    from irrevon.serve import read_dsn, workbench_assets_root

    assets_present = workbench_assets_root() is not None
    assets_note = (
        "workbench assets packaged"
        if assets_present
        else "workbench assets not built (API-only serve still works)"
    )
    try:
        with psycopg.connect(read_dsn(config.resolved_dsn())) as conn:
            row = conn.execute("SELECT 1 AS one").fetchone()
            ro = conn.execute("SHOW default_transaction_read_only").fetchone()
            if row is None or ro is None or ro[0] != "on":
                return CheckResult(
                    "serve_ready",
                    "fail",
                    "irrevon_read session is not read-only",
                    None,
                )
    except psycopg.OperationalError as err:
        return CheckResult(
            "serve_ready",
            "fail",
            f"irrevon_read role unavailable: {err}",
            "migrations out of date — run `irrevon init` (0005 creates the role)",
        )
    if not assets_present:
        return CheckResult(
            "serve_ready",
            "warn",
            f"read role OK; {assets_note}",
            "run `make web-build dist-stage`, or install from a wheel",
        )
    return CheckResult("serve_ready", "ok", f"read role OK; {assets_note}")


def collect_checks(
    config: Config, *, probe: bool = False, read_only: bool = False
) -> list[CheckResult]:
    """The full doctor check list — one producer shared by ``irrevon doctor``
    and serve's ``GET /api/v1/health`` (single-producer rule, N2 §2.9).

    ``read_only=True`` is the serve mode: the ledger checks connect as the
    SELECT-only ``irrevon_read`` role and the ``ledger_write`` round-trip is
    skipped (reported as not probed). The CLI runs the full write probe — it
    executes as the operator, not the read surface."""
    checks: list[CheckResult] = [_check_config(config), _check_identity()]
    checks.extend(_check_ledger(config, read_only=read_only))
    checks.append(_check_declarations(config))
    checks.append(_check_credentials(config))
    checks.append(_check_serve_ready(config))
    # --probe (declared read-only liveness) has nothing to reach for the
    # in-process refdest; real adapters add their cheapest read-only call (M4).
    return checks


def _payload_from(checks: list[CheckResult]) -> dict[str, Any]:
    return {
        "schema_version": "1",
        "checks": [
            {
                "name": c.name,
                "status": c.status,
                "message": c.message,
                "hint": c.hint,
            }
            for c in checks
        ],
        "ok": all(c.status != "fail" for c in checks),
    }


def doctor_payload(
    config: Config, *, probe: bool = False, read_only: bool = False
) -> dict[str, Any]:
    """The ``irrevon doctor --json`` document (``read_only=True`` = the serve
    health mode: irrevon_read connections, write probe skipped)."""
    return _payload_from(collect_checks(config, probe=probe, read_only=read_only))


def run_doctor(config: Config, *, probe: bool, as_json: bool) -> int:
    checks = collect_checks(config, probe=probe)
    ok = all(c.status != "fail" for c in checks)
    if as_json:
        print(json.dumps(_payload_from(checks)))
    else:
        for c in checks:
            print(f"[{c.status:>4}] {c.name}: {c.message}")
            if c.hint and c.status != "ok":
                print(f"       hint: {c.hint}")
        print(f"\ndoctor: {'all checks passed' if ok else 'FAILURES found'}")
    return 0 if ok else 3
