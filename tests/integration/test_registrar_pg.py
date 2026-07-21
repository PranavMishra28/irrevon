"""registerIntent against real Postgres (RFC-002 §1 semantics, T-102 wiring).

The T-101 pure decision logic executed transactionally: identity insert
arbitered, replay/variant/refresh/conflict per the member-class table, and the
INTENDED→CANCELLED genesis when the branch is already cancelled at registration.
"""

from __future__ import annotations

from datetime import UTC, datetime
from typing import Any

import pytest

from irrevon.errors import IdentityConflict
from irrevon.ledger import Ledger
from tests.integration.conftest import DBHandles
from tests.integration.driver import admin_conn

pytestmark = pytest.mark.integration

DECL = "sha256:" + "d" * 64


def _raw(**overrides: Any) -> dict[str, Any]:
    raw: dict[str, Any] = {
        "schema_version": "1",
        "stable_ids": {"order_id": "9410", "customer_ref": "C-0007"},
        "effect_type": "order.create",
        "effect_class": "IRREVERSIBLE",
        "scope": "acme-store/prod",
        "adapter_id": "refdest-c2",
        "parameters": {"line_items": [{"sku": "SKU-1", "quantity": 2}]},
        "authority_ref": "auth_approved_task_18",
        "stamped_at": datetime.now(UTC).isoformat().replace("+00:00", "Z"),
    }
    raw.update(overrides)
    return raw


def test_register_creates_persisted_record(fresh_db: DBHandles) -> None:
    with Ledger(fresh_db.app_dsn) as ledger:
        reg = ledger.register_intent(_raw(), DECL)
        assert reg.lifecycle == "PERSISTED"
        assert reg.replayed is False
        assert reg.operation_id == f"{reg.effect_id}:0"
    with admin_conn(fresh_db.admin_dsn) as conn:
        rows = conn.execute(
            "SELECT to_state FROM effect_transitions t JOIN effect_executions e "
            "USING (execution_id) WHERE e.effect_id = %s ORDER BY transition_seq",
            (reg.effect_id,),
        ).fetchall()
        assert [r["to_state"] for r in rows] == ["INTENDED", "PERSISTED"]


def test_identical_reregistration_replays(fresh_db: DBHandles) -> None:
    raw = _raw()
    with Ledger(fresh_db.app_dsn) as ledger:
        first = ledger.register_intent(raw, DECL)
        second = ledger.register_intent(raw, DECL)
    assert second.effect_id == first.effect_id
    assert second.replayed is True
    assert second.parameter_variant_digest is None
    with admin_conn(fresh_db.admin_dsn) as conn:
        count = conn.execute(
            "SELECT count(*) AS n FROM effect_records WHERE effect_id = %s",
            (first.effect_id,),
        ).fetchone()
        assert count is not None and count["n"] == 1


def test_different_effect_class_is_identity_conflict(fresh_db: DBHandles) -> None:
    """T-101/T-102 acceptance edge case, now against the real ledger."""
    with Ledger(fresh_db.app_dsn) as ledger:
        first = ledger.register_intent(_raw(), DECL)
        with pytest.raises(IdentityConflict) as excinfo:
            ledger.register_intent(_raw(effect_class="REVERSIBLE"), DECL)
        assert excinfo.value.details["effect_id"] == first.effect_id
        assert "effect_class" in excinfo.value.details["mismatches"]


def test_resynthesized_parameters_record_a_variant(fresh_db: DBHandles) -> None:
    with Ledger(fresh_db.app_dsn) as ledger:
        first = ledger.register_intent(_raw(), DECL)
        second = ledger.register_intent(
            _raw(parameters={"line_items": [{"sku": "SKU-1", "quantity": 5}]}), DECL
        )
    assert second.effect_id == first.effect_id
    assert second.replayed is True
    assert second.parameter_variant_digest is not None
    with admin_conn(fresh_db.admin_dsn) as conn:
        variants = conn.execute(
            "SELECT parameters_digest FROM parameter_variants WHERE effect_id = %s",
            (first.effect_id,),
        ).fetchall()
        assert len(variants) == 1
        assert variants[0]["parameters_digest"] == second.parameter_variant_digest


def test_fresh_authority_appends_refresh(fresh_db: DBHandles) -> None:
    with Ledger(fresh_db.app_dsn) as ledger:
        first = ledger.register_intent(_raw(), DECL)
        second = ledger.register_intent(
            _raw(authority_ref="auth_approved_task_22"), DECL
        )
    assert second.authority_refresh is True
    with admin_conn(fresh_db.admin_dsn) as conn:
        links = conn.execute(
            "SELECT count(*) AS n FROM effect_authorities WHERE effect_id = %s",
            (first.effect_id,),
        ).fetchone()
        assert links is not None and links["n"] == 2


def test_register_on_cancelled_branch_cancels_at_genesis(
    fresh_db: DBHandles,
) -> None:
    """RFC-002 §2.3: INTENDED→CANCELLED is taken instead when the branch is
    already cancelled at registration — the record can never dispatch."""
    with admin_conn(fresh_db.admin_dsn) as conn:
        conn.execute(
            "INSERT INTO branch_cancellations (branch_ref, reason) "
            "VALUES ('wf_branch_dead', 'workflow abandoned')"
        )
    with Ledger(fresh_db.app_dsn) as ledger:
        reg = ledger.register_intent(_raw(branch_ref="wf_branch_dead"), DECL)
        assert reg.lifecycle == "CANCELLED"
