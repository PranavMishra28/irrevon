"""Generated-from discipline (RFC-002 §3): the SQL seed tables ARE the ratified
state model — cross-checked against detent.statetable, the single in-code
encoding. Divergence anywhere is a migration bug, never resolved by editing
either side casually (amendment territory)."""

from __future__ import annotations

import pytest

from detent.statetable import (
    LEGAL_ACTIONS,
    LEGAL_ATTACHMENTS,
    LEGAL_STATUS_EDGES,
    LIFECYCLE_EDGES,
)
from tests.integration.conftest import DBHandles
from tests.integration.driver import admin_conn

pytestmark = pytest.mark.integration


def test_lifecycle_edges_seed_matches_statetable(fresh_db: DBHandles) -> None:
    with admin_conn(fresh_db.admin_dsn) as conn:
        rows = conn.execute(
            "SELECT from_state, to_state, cause, actor FROM lifecycle_edges"
        ).fetchall()
    seeded = {
        (r["from_state"], r["to_state"], r["cause"], r["actor"]) for r in rows
    }
    assert seeded == set(LIFECYCLE_EDGES)


def test_attachment_seed_matches_statetable(fresh_db: DBHandles) -> None:
    with admin_conn(fresh_db.admin_dsn) as conn:
        rows = conn.execute(
            "SELECT frontier, classification FROM classification_attachments"
        ).fetchall()
    assert {(r["frontier"], r["classification"]) for r in rows} == set(
        LEGAL_ATTACHMENTS
    )


def test_resolution_action_seed_matches_statetable(fresh_db: DBHandles) -> None:
    with admin_conn(fresh_db.admin_dsn) as conn:
        rows = conn.execute(
            "SELECT classification, action FROM resolution_actions"
        ).fetchall()
    assert {(r["classification"], r["action"]) for r in rows} == set(LEGAL_ACTIONS)


def test_status_edge_seed_matches_statetable(fresh_db: DBHandles) -> None:
    with admin_conn(fresh_db.admin_dsn) as conn:
        rows = conn.execute(
            "SELECT from_status, to_status FROM resolution_status_edges"
        ).fetchall()
    assert {(r["from_status"], r["to_status"]) for r in rows} == set(
        LEGAL_STATUS_EDGES
    )
