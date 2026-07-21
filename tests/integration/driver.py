"""Matrix-test driver: brings executions to arbitrary lifecycle states.

The driver writes prefix chains DIRECTLY as the superuser (bypassing the locked
functions — that is the point: the transition-under-test goes through
``ledger_transition``, while setup is oracle-controlled). It also writes the
supporting evidence (gate decisions, attempts, receipts) the ledger auditor
demands, so matrix tests run under the standing §3.5 post-condition.
"""

from __future__ import annotations

import hashlib
import uuid
from typing import Any

import psycopg
from psycopg.rows import dict_row
from psycopg.types.json import Jsonb

# Prefix chains per target state: (from, to, cause, actor) per RFC-002 §3.1.
CHAINS: dict[str, list[tuple[str | None, str, str, str]]] = {
    "INTENDED": [(None, "INTENDED", "register", "registrar")],
    "PERSISTED": [
        (None, "INTENDED", "register", "registrar"),
        ("INTENDED", "PERSISTED", "durable_write", "registrar"),
    ],
    "CANCELLED": [
        (None, "INTENDED", "register", "registrar"),
        ("INTENDED", "CANCELLED", "branch_cancelled", "registrar"),
    ],
    "DISPATCHED": [
        (None, "INTENDED", "register", "registrar"),
        ("INTENDED", "PERSISTED", "durable_write", "registrar"),
        ("PERSISTED", "DISPATCHED", "gate_allow", "gate"),
    ],
    "SETTLED_COMMITTED": [
        (None, "INTENDED", "register", "registrar"),
        ("INTENDED", "PERSISTED", "durable_write", "registrar"),
        ("PERSISTED", "DISPATCHED", "gate_allow", "gate"),
        ("DISPATCHED", "SETTLED_COMMITTED", "receipt_ok", "dispatcher"),
    ],
    "SETTLED_FAILED": [
        (None, "INTENDED", "register", "registrar"),
        ("INTENDED", "PERSISTED", "durable_write", "registrar"),
        ("PERSISTED", "DISPATCHED", "gate_allow", "gate"),
        ("DISPATCHED", "SETTLED_FAILED", "receipt_failed", "dispatcher"),
    ],
    "AMBIGUOUS": [
        (None, "INTENDED", "register", "registrar"),
        ("INTENDED", "PERSISTED", "durable_write", "registrar"),
        ("PERSISTED", "DISPATCHED", "gate_allow", "gate"),
        ("DISPATCHED", "AMBIGUOUS", "receipt_lost", "dispatcher"),
    ],
}


def make_effect(
    conn: psycopg.Connection[dict[str, Any]],
    *,
    scope: str = "test-scope",
    effect_type: str = "order.create",
    branch_ref: str | None = None,
) -> str:
    """Insert an effect record (+ fresh authority) with a unique synthetic id."""
    effect_id = hashlib.sha256(uuid.uuid4().bytes).hexdigest()
    conn.execute(
        """
        INSERT INTO effect_records (effect_id, effect_type, effect_class, scope,
          stable_ids, adapter_id, declaration_digest, parameters,
          parameters_digest, contract_canonical, branch_ref)
        VALUES (%s, %s, 'IRREVERSIBLE', %s, %s, 'refdest-c2', 'sha256:0', %s,
                'sha256:0', %s, %s)
        """,
        (effect_id, effect_type, scope, Jsonb({"test_id": effect_id[:8]}),
         Jsonb({"driver": True}), effect_id.encode(), branch_ref),
    )
    row = conn.execute(
        """
        INSERT INTO authorities (authority_ref, scope, stamped_at)
        VALUES ('auth_driver', %s, now()) RETURNING authority_id
        """,
        (scope,),
    ).fetchone()
    assert row is not None
    conn.execute(
        "INSERT INTO effect_authorities (effect_id, authority_id) VALUES (%s, %s)",
        (effect_id, row["authority_id"]),
    )
    return effect_id


def make_execution_at(
    conn: psycopg.Connection[dict[str, Any]],
    effect_id: str,
    state: str,
    *,
    step: int = 0,
) -> int:
    """Create an execution whose frontier is ``state``, with the supporting
    evidence rows (decision/attempt/receipt) the auditor requires."""
    chain = CHAINS[state]
    row = conn.execute(
        """
        INSERT INTO effect_executions (effect_id, step, operation_id, opened_by)
        VALUES (%s, %s, %s, 'register') RETURNING execution_id
        """,
        (effect_id, step, f"{effect_id}:{step}"),
    ).fetchone()
    assert row is not None
    execution_id: int = row["execution_id"]

    dispatched = any(t[1] == "DISPATCHED" for t in chain)
    attempt_id: int | None = None
    if dispatched:
        decision = conn.execute(
            """
            INSERT INTO gate_decisions (effect_id, execution_id, variant, outcome,
              deny_check, checks, evidence)
            VALUES (%s, %s, 'dispatch', 'ALLOW', NULL, %s, %s)
            RETURNING decision_id
            """,
            (effect_id, execution_id, Jsonb([]), Jsonb({"driver": True})),
        ).fetchone()
        assert decision is not None
        attempt = conn.execute(
            """
            INSERT INTO dispatch_attempts (execution_id, attempt_no, kind, adapter_id,
              declaration_digest, idempotency_key, request_digest, gate_decision_id)
            VALUES (%s, 1, 'primary', 'refdest-c2', 'sha256:0', %s, 'sha256:0', %s)
            RETURNING attempt_id
            """,
            (execution_id, f"{effect_id}:{step}", decision["decision_id"]),
        ).fetchone()
        assert attempt is not None
        attempt_id = attempt["attempt_id"]

    receipt_id: int | None = None
    receipt_map = {
        "SETTLED_COMMITTED": ("OK", None),
        "SETTLED_FAILED": ("FAILED", "TERMINAL"),
        "AMBIGUOUS": ("LOST", None),
    }
    if state in receipt_map and attempt_id is not None:
        outcome, failure_kind = receipt_map[state]
        receipt = conn.execute(
            """
            INSERT INTO dispatch_receipts (attempt_id, transport_outcome, failure_kind,
              destination_ref, evidence, recorded_by)
            VALUES (%s, %s, %s, 'dest_driver', %s, 'dispatcher')
            RETURNING receipt_id
            """,
            (attempt_id, outcome, failure_kind, Jsonb({"driver": True})),
        ).fetchone()
        assert receipt is not None
        receipt_id = receipt["receipt_id"]

    for from_state, to_state, cause, actor in chain:
        evidence: dict[str, Any] = {"driver": True}
        if from_state == "AMBIGUOUS" or (
            to_state in ("SETTLED_COMMITTED", "SETTLED_FAILED", "AMBIGUOUS")
            and receipt_id is not None
        ):
            evidence["receipt_id"] = receipt_id
        conn.execute(
            """
            INSERT INTO effect_transitions (execution_id, from_state, to_state, cause,
              actor, evidence)
            VALUES (%s, %s, %s, %s, %s, %s)
            """,
            (execution_id, from_state, to_state, cause, actor, Jsonb(evidence)),
        )
    return execution_id


def add_dispatch_evidence(
    conn: psycopg.Connection[dict[str, Any]], effect_id: str, execution_id: int
) -> int:
    """Gate decision + attempt rows for an execution that just entered
    DISPATCHED through ledger_transition in a matrix test (auditor rule 6)."""
    decision = conn.execute(
        """
        INSERT INTO gate_decisions (effect_id, execution_id, variant, outcome,
          deny_check, checks, evidence)
        VALUES (%s, %s, 'dispatch', 'ALLOW', NULL, %s, %s)
        RETURNING decision_id
        """,
        (effect_id, execution_id, Jsonb([]), Jsonb({"driver": True})),
    ).fetchone()
    assert decision is not None
    attempt = conn.execute(
        """
        INSERT INTO dispatch_attempts (execution_id, attempt_no, kind, adapter_id,
          declaration_digest, idempotency_key, request_digest, gate_decision_id)
        VALUES (%s,
                (SELECT COALESCE(MAX(attempt_no), 0) + 1 FROM dispatch_attempts
                 WHERE execution_id = %s),
                'primary', 'refdest-c2', 'sha256:0', %s, 'sha256:0', %s)
        RETURNING attempt_id
        """,
        (execution_id, execution_id, f"{effect_id}:0", decision["decision_id"]),
    ).fetchone()
    assert attempt is not None
    return int(attempt["attempt_id"])


def add_receipt(
    conn: psycopg.Connection[dict[str, Any]],
    execution_id: int,
    transport_outcome: str,
    failure_kind: str | None = None,
) -> int:
    """Receipt row on the execution's latest attempt (auditor rule 4)."""
    attempt = conn.execute(
        """
        SELECT attempt_id FROM dispatch_attempts WHERE execution_id = %s
        ORDER BY attempt_no DESC LIMIT 1
        """,
        (execution_id,),
    ).fetchone()
    assert attempt is not None
    receipt = conn.execute(
        """
        INSERT INTO dispatch_receipts (attempt_id, transport_outcome, failure_kind,
          destination_ref, evidence, recorded_by)
        VALUES (%s, %s, %s, 'dest_driver', %s, 'dispatcher')
        RETURNING receipt_id
        """,
        (attempt["attempt_id"], transport_outcome, failure_kind, Jsonb({"driver": True})),
    ).fetchone()
    assert receipt is not None
    return int(receipt["receipt_id"])


def admin_conn(dsn: str) -> psycopg.Connection[dict[str, Any]]:
    return psycopg.connect(dsn, row_factory=dict_row, autocommit=True)


def transition_count(conn: psycopg.Connection[dict[str, Any]]) -> int:
    row = conn.execute("SELECT count(*) AS n FROM effect_transitions").fetchone()
    assert row is not None
    return int(row["n"])
