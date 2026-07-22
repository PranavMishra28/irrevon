"""Route conformance against a real engine-seeded ledger (integration tier):
Q1 filters + keyset cursor, schema validation of served items, route-2 detail,
inspect byte-parity with the CLI (the single-producer lock), Q2 findings,
health, and the row-count-proof method rejection."""

from __future__ import annotations

import json
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

import psycopg
import pytest
from jsonschema import Draft202012Validator
from psycopg.rows import dict_row

from irrevon.cli import main
from irrevon.contract import load_schema
from tests.serve.conftest import DBHandles, RunningServer, _app, _start

pytestmark = pytest.mark.integration

_LEDGER_TABLES = (
    "effect_records",
    "effect_transitions",
    "gate_decisions",
    "findings",
    "finding_resolutions",
    "dispatch_receipts",
)


def _counts(dsn: str) -> dict[str, int]:
    with psycopg.connect(dsn, row_factory=dict_row) as conn:
        out: dict[str, int] = {}
        for table in _LEDGER_TABLES:
            row = conn.execute(f"SELECT count(*) AS n FROM {table}").fetchone()
            assert row is not None
            out[table] = int(row["n"])
        return out


# ── Q1: /api/v1/effects ───────────────────────────────────────────────────────


def test_q1_item_shape_and_schema_conformance(
    seeded_server: tuple[RunningServer, str],
) -> None:
    server, effect_id = seeded_server
    status, headers, payload = server.get_json("/api/v1/effects")
    assert status == 200
    assert headers["irrevon-schema-version"] == "1"
    assert set(payload) == {"schema_version", "data", "has_more", "next_cursor", "as_of"}
    items = payload["data"]
    assert [i["record"]["effect_id"] for i in items] == [effect_id]

    item = items[0]
    assert set(item) == {"record", "classification", "finding"}
    assert item["classification"] == "CONFIRMED_UNIQUE"
    assert item["record"]["lifecycle"] == "SETTLED_COMMITTED"
    # stable_ids served as stored (loopback trust domain, N2 §2.1 ruling)
    assert item["record"]["stable_ids"] == {"order_id": "serve-9410"}

    Draft202012Validator(load_schema("effect-record.schema.json")).validate(
        item["record"]
    )
    Draft202012Validator(load_schema("reconciliation-finding.schema.json")).validate(
        item["finding"]
    )


def test_q1_filters(seeded_server: tuple[RunningServer, str]) -> None:
    server, effect_id = seeded_server

    def ids(query: str) -> list[str]:
        status, _, payload = server.get_json(f"/api/v1/effects?{query}")
        assert status == 200, payload
        return [i["record"]["effect_id"] for i in payload["data"]]

    assert ids("lifecycle=SETTLED_COMMITTED") == [effect_id]
    assert ids("lifecycle=AMBIGUOUS") == []
    assert ids("lifecycle=AMBIGUOUS&lifecycle=SETTLED_COMMITTED") == [effect_id]
    assert ids("classification=CONFIRMED_UNIQUE") == [effect_id]
    assert ids("classification=UNRECONCILED") == []
    assert ids("effect_type=order.create") == [effect_id]
    assert ids("effect_type=nothing.of.the.kind") == []
    assert ids("effect_class=IRREVERSIBLE") == [effect_id]
    assert ids("scope=serve/prod") == [effect_id]
    assert ids("scope=other/prod") == []
    assert ids("from=2000-01-01T00:00:00Z") == [effect_id]
    assert ids("to=2000-01-01T00:00:00Z") == []


def test_q1_rejects_malformed_params(
    seeded_server: tuple[RunningServer, str],
) -> None:
    server, _ = seeded_server
    for query in (
        "lifecycle=NOT_A_STATE",
        "classification=NOT_A_CLASS",
        "from=yesterday",
        "cursor=%%%not-base64",
        "cursor=aGVsbG8",  # base64 of "hello" — not a cursor document
        "limit=zero",
        "limit=-1",
    ):
        status, _, payload = server.get_json(f"/api/v1/effects?{query}")
        assert status == 400, f"{query} → {status}"
        assert payload["error"]["code"] == "query_invalid"


def _register_effects(handles: DBHandles, n: int) -> list[str]:
    from irrevon.adapters.base import declarations_dir, load_declaration
    from irrevon.adapters.refdest import RefDest, RefdestAdapter
    from irrevon.api import Engine

    declaration = load_declaration(declarations_dir() / "refdest-c2.capability.json")
    adapter = RefdestAdapter("refdest-c2", declaration, instance=RefDest(seed=11))
    out: list[str] = []
    with Engine(handles.app_dsn, {"refdest-c2": adapter}) as engine:
        engine.boot()
        for i in range(n):
            reg = engine.register_intent(
                {
                    "schema_version": "1",
                    "stable_ids": {"payout_id": f"PO-{i:04d}"},
                    "effect_type": "payout.create",
                    "effect_class": "IRREVERSIBLE",
                    "scope": "cursor/prod",
                    "adapter_id": "refdest-c2",
                    "parameters": {"amount_minor": 100 + i},
                    "authority_ref": f"auth_cursor_{i}",
                    "stamped_at": datetime.now(UTC)
                    .isoformat()
                    .replace("+00:00", "Z"),
                }
            )
            out.append(reg.effect_id)
    return out


def test_q1_keyset_cursor_walks_the_full_set_exactly_once(
    seeded_effect: tuple[DBHandles, str], tmp_path: Path
) -> None:
    handles, flagship = seeded_effect
    registered = _register_effects(handles, 5)
    expected = 6  # 5 persisted + the flagship

    for running in _start(_app(handles.admin_dsn, tmp_path / "a.json")):
        seen: list[str] = []
        cursor: str | None = None
        pages = 0
        while True:
            query = "limit=2" + (f"&cursor={cursor}" if cursor else "")
            status, _, payload = running.get_json(f"/api/v1/effects?{query}")
            assert status == 200
            seen.extend(i["record"]["effect_id"] for i in payload["data"])
            pages += 1
            if not payload["has_more"]:
                assert payload["next_cursor"] is None
                break
            cursor = payload["next_cursor"]
            assert cursor is not None
        assert pages == 3
        assert len(seen) == expected
        assert len(set(seen)) == expected, "an effect appeared twice across pages"
        assert set(seen) == {flagship, *registered}
        # stable order: created_at DESC, effect_id DESC — one full unpaged read
        status, _, unpaged = running.get_json("/api/v1/effects?limit=500")
        assert [i["record"]["effect_id"] for i in unpaged["data"]] == seen


def test_q1_limit_clamps_at_500_without_error(
    seeded_server: tuple[RunningServer, str],
) -> None:
    server, _ = seeded_server
    status, _, payload = server.get_json("/api/v1/effects?limit=99999")
    assert status == 200  # clamp, don't error (dx-api §4 Q1)
    assert payload["has_more"] is False


# ── route 2: /api/v1/effects/{id} ─────────────────────────────────────────────


def test_effect_detail_shape(seeded_server: tuple[RunningServer, str]) -> None:
    server, effect_id = seeded_server
    status, _, payload = server.get_json(f"/api/v1/effects/{effect_id}")
    assert status == 200
    assert set(payload) == {"schema_version", "record", "classification", "finding"}
    assert payload["record"]["effect_id"] == effect_id
    assert payload["classification"] == "CONFIRMED_UNIQUE"


def test_effect_detail_unknown_id_is_404(
    seeded_server: tuple[RunningServer, str],
) -> None:
    server, _ = seeded_server
    status, _, payload = server.get_json("/api/v1/effects/" + "f" * 64)
    assert status == 404
    assert payload["error"]["code"] == "not_found"
    status, _, payload = server.get_json("/api/v1/effects/not-an-effect-id")
    assert status == 404


# ── route 3: inspect byte-parity (the single-producer lock) ───────────────────


def test_inspect_route_is_byte_identical_to_cli_inspect_json(
    seeded_server: tuple[RunningServer, str],
    capsys: pytest.CaptureFixture[str],
) -> None:
    server, effect_id = seeded_server
    status, _, body = server.request("GET", f"/api/v1/effects/{effect_id}/inspect")
    assert status == 200

    rc = main([
        "inspect", effect_id, "--dsn", server.app.dsn, "--json", "--reveal",
    ])
    assert rc == 0
    cli_bytes = capsys.readouterr().out.strip().encode("utf-8")
    assert body == cli_bytes, "serve and CLI inspect must share ONE producer"

    payload = json.loads(body)
    assert payload["integrity"]["matches"] is True
    assert [d["outcome"] for d in payload["gate_decisions"]] == ["ALLOW", "DENY"]
    assert payload["record"]["stable_ids"] == {"order_id": "serve-9410"}


def test_inspect_unknown_id_is_404(
    seeded_server: tuple[RunningServer, str],
) -> None:
    server, _ = seeded_server
    status, _, payload = server.get_json(
        "/api/v1/effects/" + "f" * 64 + "/inspect"
    )
    assert status == 404
    assert payload["error"]["code"] == "not_found"


# ── Q2: /api/v1/findings ──────────────────────────────────────────────────────


def test_q2_shape_filters_and_schema(
    seeded_server: tuple[RunningServer, str],
) -> None:
    server, effect_id = seeded_server
    status, _, payload = server.get_json("/api/v1/findings")
    assert status == 200
    assert set(payload) == {"schema_version", "data", "has_more", "next_cursor", "as_of"}
    findings = payload["data"]
    assert len(findings) == 1
    finding = findings[0]
    assert finding["subject"] == {"effect_id": effect_id}
    assert finding["classification"] == "CONFIRMED_UNIQUE"
    assert finding["evidence"]["redaction"] == "digest_only"
    assert finding["evidence"]["bundle"] is None
    Draft202012Validator(load_schema("reconciliation-finding.schema.json")).validate(
        finding
    )
    resolved_status = finding["resolution"]["status"]

    def ids(query: str) -> list[str]:
        status, _, page = server.get_json(f"/api/v1/findings?{query}")
        assert status == 200, page
        return [f["finding_id"] for f in page["data"]]

    assert ids("classification=CONFIRMED_UNIQUE") == [finding["finding_id"]]
    assert ids("classification=ORPHANED") == []
    assert ids(f"resolution_status={resolved_status}") == [finding["finding_id"]]
    other = "OPEN" if resolved_status != "OPEN" else "CLOSED"
    assert ids(f"resolution_status={other}") == []
    assert ids(f"subject_effect_id={effect_id}") == [finding["finding_id"]]
    assert ids("subject_effect_id=" + "f" * 64) == []
    assert ids("adapter=refdest-c2") == [finding["finding_id"]]
    assert ids("adapter=refdest-c9") == []

    status, _, err = server.get_json("/api/v1/findings?resolution_status=BOGUS")
    assert status == 400 and err["error"]["code"] == "query_invalid"


# ── health (route 7) ──────────────────────────────────────────────────────────


def test_health_is_green_with_a_real_db(
    seeded_server: tuple[RunningServer, str],
) -> None:
    server, _ = seeded_server
    status, headers, payload = server.get_json("/api/v1/health")
    assert status == 200
    assert headers["irrevon-schema-version"] == "1"
    by_name = {c["name"]: c for c in payload["checks"]}
    assert by_name["ledger_db"]["status"] == "ok"
    assert by_name["serve_ready"]["status"] in ("ok", "warn")  # warn = no assets
    # The write probe is a CLI-doctor affordance; the served payload reports
    # the read-only serve context honestly instead of running it.
    assert by_name["ledger_write"]["status"] == "skipped"
    assert by_name["ledger_write"]["message"] == "not probed (read-only serve context)"
    assert payload["ok"] is True


def test_health_path_opens_no_write_capable_connection(
    seeded_server: tuple[RunningServer, str],
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """B1 regression (adversarial review 2026-07-21): GET /api/v1/health must
    never open a write-capable connection. Every DB session the health path
    opens is interrogated live: the session user must be irrevon_read, the
    session must default to read-only, and — the grants-based proof — the
    catalog must show zero non-SELECT table grants for that session's user."""
    import psycopg.rows

    from irrevon.serve import READ_ROLE

    server, _ = seeded_server
    server.app._health_cache = None  # force a fresh doctor pass through the DB

    observed: list[dict[str, Any]] = []
    real_connect = psycopg.connect

    def recording_connect(conninfo: str = "", **kwargs: Any) -> Any:
        conn = real_connect(conninfo, **kwargs)
        with conn.cursor(row_factory=psycopg.rows.tuple_row) as cur:
            cur.execute(
                """
                SELECT current_user,
                       current_setting('default_transaction_read_only'),
                       (SELECT count(*)
                        FROM information_schema.role_table_grants
                        WHERE grantee = current_user
                          AND privilege_type <> 'SELECT')
                """
            )
            row = cur.fetchone()
        conn.rollback()  # leave the connection exactly as the caller expects
        assert row is not None
        observed.append(
            {
                "conninfo": str(conninfo),
                "user": row[0],
                "default_read_only": row[1],
                "non_select_grants": int(row[2]),
            }
        )
        return conn

    monkeypatch.setattr(psycopg, "connect", recording_connect)
    status, _, payload = server.get_json("/api/v1/health")
    assert status == 200
    assert observed, "the health path must actually open DB connections"
    for session in observed:
        assert session["user"] == READ_ROLE, (
            f"health opened a connection as {session['user']!r} — "
            f"only {READ_ROLE} is allowed on the serve surface"
        )
        assert f"user={READ_ROLE}" in session["conninfo"]
        assert session["default_read_only"] == "on"
        assert session["non_select_grants"] == 0, (
            "the health path executed under a role holding write grants"
        )
    by_name = {c["name"]: c for c in payload["checks"]}
    assert by_name["ledger_write"]["status"] == "skipped"
    assert payload["ok"] is True


# ── method rejection with row-count proof (§5.1 item 2) ───────────────────────


def test_write_methods_change_zero_ledger_rows(
    seeded_server: tuple[RunningServer, str],
) -> None:
    server, effect_id = seeded_server
    before = _counts(server.app.dsn)
    for method in ("POST", "PUT", "PATCH", "DELETE"):
        for route in (
            "/api/v1/effects",
            f"/api/v1/effects/{effect_id}",
            "/api/v1/findings",
            "/api/v1/health",
        ):
            status, _, _ = server.request(method, route)
            assert status == 405
    assert _counts(server.app.dsn) == before, (
        "a write method changed ledger rows — the read-only surface is broken"
    )
