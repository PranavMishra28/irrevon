-- Detent ledger migration 0003 — the locked transition writer (RFC-002 §2.3).
--
-- detent_app has NO INSERT privilege on effect_transitions, effect_executions,
-- findings, or finding_resolutions. All lifecycle writes go through these
-- SECURITY DEFINER functions, owned by the migration role. Any violation
-- raises; nothing is written. Custom SQLSTATEs (mapped to typed errors by
-- src/detent/ledger/db.py):
--   DT001 illegal lifecycle edge     DT002 stale expected_from / lost race
--   DT003 illegal classification attachment
--   DT004 illegal resolution         DT005 precondition violation

-- ── ledger_open_execution ─────────────────────────────────────────────────────
-- Locks the identity row, allocates the next step, inserts the execution plus
-- its genesis transitions (NULL→INTENDED→PERSISTED in one transaction; INTENDED
-- is never externally observable alone; INTENDED→CANCELLED taken instead when
-- the branch is already cancelled at open time).

CREATE FUNCTION ledger_open_execution(
  p_effect_id text,
  p_opened_by text
) RETURNS TABLE (execution_id bigint, step integer, operation_id text, state text)
LANGUAGE plpgsql SECURITY DEFINER SET search_path = public, pg_temp AS $$
DECLARE
  v_record   effect_records%ROWTYPE;
  v_step     integer;
  v_frontier text;
  v_exec_id  bigint;
  v_op_id    text;
  v_cancelled boolean;
  v_state    text;
BEGIN
  SELECT * INTO v_record FROM effect_records r
    WHERE r.effect_id = p_effect_id FOR UPDATE;
  IF NOT FOUND THEN
    RAISE EXCEPTION 'no effect record %', p_effect_id USING ERRCODE = 'DT005';
  END IF;

  SELECT COALESCE(MAX(e.step) + 1, 0) INTO v_step
    FROM effect_executions e WHERE e.effect_id = p_effect_id;

  IF p_opened_by = 'register' THEN
    IF v_step <> 0 THEN
      RAISE EXCEPTION 'register may only open the first execution (effect %)',
        p_effect_id USING ERRCODE = 'DT005';
    END IF;
  ELSE
    -- "Try again" after a terminal state is a new execution (§3.1); the prior
    -- execution must be SETTLED_FAILED for both explicit retry paths (§5.3).
    SELECT f.frontier INTO v_frontier
      FROM execution_frontiers f
      WHERE f.effect_id = p_effect_id
      ORDER BY f.step DESC LIMIT 1;
    IF v_frontier IS DISTINCT FROM 'SETTLED_FAILED' THEN
      RAISE EXCEPTION
        'non-initial execution requires latest frontier SETTLED_FAILED, found % (effect %)',
        v_frontier, p_effect_id USING ERRCODE = 'DT005';
    END IF;
  END IF;

  v_op_id := p_effect_id || ':' || v_step::text;
  INSERT INTO effect_executions (effect_id, step, operation_id, opened_by)
    VALUES (p_effect_id, v_step, v_op_id, p_opened_by)
    RETURNING effect_executions.execution_id INTO v_exec_id;

  v_cancelled := v_record.branch_ref IS NOT NULL AND EXISTS (
    SELECT 1 FROM branch_cancellations b WHERE b.branch_ref = v_record.branch_ref
  );

  INSERT INTO effect_transitions (execution_id, from_state, to_state, cause, actor, evidence)
    VALUES (v_exec_id, NULL, 'INTENDED', 'register', 'registrar',
            jsonb_build_object('opened_by', p_opened_by));
  IF v_cancelled THEN
    INSERT INTO effect_transitions (execution_id, from_state, to_state, cause, actor, evidence)
      VALUES (v_exec_id, 'INTENDED', 'CANCELLED', 'branch_cancelled', 'registrar',
              jsonb_build_object('branch_ref', v_record.branch_ref));
    v_state := 'CANCELLED';
  ELSE
    INSERT INTO effect_transitions (execution_id, from_state, to_state, cause, actor, evidence)
      VALUES (v_exec_id, 'INTENDED', 'PERSISTED', 'durable_write', 'registrar',
              jsonb_build_object('opened_by', p_opened_by));
    v_state := 'PERSISTED';
  END IF;

  RETURN QUERY SELECT v_exec_id, v_step, v_op_id, v_state;
END $$;

-- ── ledger_transition ─────────────────────────────────────────────────────────
-- Locks the execution row, derives the current frontier, REQUIRES
-- expected_from = frontier, validates the edge (incl. cause/actor legality)
-- against the ratified §3.1 table, and inserts atomically.

CREATE FUNCTION ledger_transition(
  p_execution_id  bigint,
  p_expected_from text,
  p_to_state      text,
  p_cause         text,
  p_actor         text,
  p_evidence      jsonb
) RETURNS bigint
LANGUAGE plpgsql SECURITY DEFINER SET search_path = public, pg_temp AS $$
DECLARE
  v_frontier text;
  v_seq      bigint;
BEGIN
  PERFORM 1 FROM effect_executions e
    WHERE e.execution_id = p_execution_id FOR UPDATE;
  IF NOT FOUND THEN
    RAISE EXCEPTION 'no execution %', p_execution_id USING ERRCODE = 'DT005';
  END IF;

  IF p_evidence IS NULL OR jsonb_typeof(p_evidence) <> 'object' THEN
    RAISE EXCEPTION 'evidence must be a JSON object' USING ERRCODE = 'DT005';
  END IF;

  SELECT t.to_state INTO v_frontier
    FROM effect_transitions t
    WHERE t.execution_id = p_execution_id
    ORDER BY t.transition_seq DESC LIMIT 1;

  IF v_frontier IS DISTINCT FROM p_expected_from THEN
    RAISE EXCEPTION
      'stale expected_from: frontier is %, caller expected % (execution %)',
      COALESCE(v_frontier, '<genesis>'), COALESCE(p_expected_from, '<genesis>'),
      p_execution_id
      USING ERRCODE = 'DT002';
  END IF;

  IF NOT EXISTS (
    SELECT 1 FROM lifecycle_edges le
    WHERE le.from_state IS NOT DISTINCT FROM p_expected_from
      AND le.to_state = p_to_state AND le.cause = p_cause AND le.actor = p_actor
  ) THEN
    RAISE EXCEPTION
      'illegal transition % -> % (cause %, actor %) is not in the ratified table (RFC-002 §3.1)',
      COALESCE(p_expected_from, '<genesis>'), p_to_state, p_cause, p_actor
      USING ERRCODE = 'DT001';
  END IF;

  INSERT INTO effect_transitions (execution_id, from_state, to_state, cause, actor, evidence)
    VALUES (p_execution_id, p_expected_from, p_to_state, p_cause, p_actor, p_evidence)
    RETURNING transition_seq INTO v_seq;
  RETURN v_seq;
END $$;

-- ── ledger_attach_finding ─────────────────────────────────────────────────────
-- Classify-and-settle discipline (§3.2): no finding may attach while the
-- frontier is in-flight; legality per the ratified attachment table. ORPHANED
-- is destination-keyed only (effect_id IS NULL). CONFIRMED_UNIQUE auto-resolves
-- ACCEPTED_AS_IS (system actor) and CLOSES in the same transaction (§3.3).

CREATE FUNCTION ledger_attach_finding(
  p_effect_id       text,
  p_adapter_id      text,
  p_destination_ref text,
  p_classification  text,
  p_excess          integer,
  p_evidence        jsonb,
  p_evidence_digest text,
  p_created_by      text
) RETURNS bigint
LANGUAGE plpgsql SECURITY DEFINER SET search_path = public, pg_temp AS $$
DECLARE
  v_frontier   text;
  v_finding_id bigint;
BEGIN
  IF p_evidence IS NULL OR jsonb_typeof(p_evidence) <> 'object' THEN
    RAISE EXCEPTION 'evidence must be a JSON object' USING ERRCODE = 'DT005';
  END IF;

  IF p_effect_id IS NULL THEN
    IF p_classification <> 'ORPHANED' THEN
      RAISE EXCEPTION 'record-less findings must be ORPHANED (§3.2)'
        USING ERRCODE = 'DT003';
    END IF;
  ELSE
    IF p_classification = 'ORPHANED' THEN
      RAISE EXCEPTION 'ORPHANED never attaches to a record (§3.2)'
        USING ERRCODE = 'DT003';
    END IF;
    PERFORM 1 FROM effect_records r WHERE r.effect_id = p_effect_id FOR UPDATE;
    IF NOT FOUND THEN
      RAISE EXCEPTION 'no effect record %', p_effect_id USING ERRCODE = 'DT005';
    END IF;
    SELECT f.frontier INTO v_frontier
      FROM execution_frontiers f
      WHERE f.effect_id = p_effect_id
      ORDER BY f.step DESC LIMIT 1;
    IF NOT EXISTS (
      SELECT 1 FROM classification_attachments ca
      WHERE ca.frontier = COALESCE(v_frontier, 'INTENDED')
        AND ca.classification = p_classification
    ) THEN
      RAISE EXCEPTION
        'illegal attachment: % on frontier % (RFC-002 §3.2)',
        p_classification, COALESCE(v_frontier, '<none>')
        USING ERRCODE = 'DT003';
    END IF;
  END IF;

  INSERT INTO findings (effect_id, adapter_id, destination_ref, classification,
                        excess_effect_count, evidence, evidence_digest, created_by)
    VALUES (p_effect_id, p_adapter_id, p_destination_ref, p_classification,
            p_excess, p_evidence, p_evidence_digest, p_created_by)
    RETURNING findings.finding_id INTO v_finding_id;

  IF p_classification = 'CONFIRMED_UNIQUE' THEN
    INSERT INTO finding_resolutions (finding_id, from_status, to_status, evidence, actor)
      VALUES (v_finding_id, 'OPEN', 'ACCEPTED_AS_IS',
              jsonb_build_object('auto', 'confirmed_unique_settle'), 'system');
    INSERT INTO finding_resolutions (finding_id, from_status, to_status, evidence, actor)
      VALUES (v_finding_id, 'ACCEPTED_AS_IS', 'CLOSED',
              jsonb_build_object('auto', 'confirmed_unique_settle'), 'system');
  END IF;

  RETURN v_finding_id;
END $$;

-- ── ledger_resolve ────────────────────────────────────────────────────────────
-- Same pattern over §3.3: finding row lock, first-write-wins via
-- UNIQUE (finding_id, from_status), status-chain + classification×action
-- legality from the ratified tables.

CREATE FUNCTION ledger_resolve(
  p_finding_id  bigint,
  p_from_status text,
  p_to_status   text,
  p_actor       text,
  p_evidence    jsonb
) RETURNS bigint
LANGUAGE plpgsql SECURITY DEFINER SET search_path = public, pg_temp AS $$
DECLARE
  v_classification text;
  v_current        text;
  v_seq            bigint;
BEGIN
  SELECT f.classification INTO v_classification
    FROM findings f WHERE f.finding_id = p_finding_id FOR UPDATE;
  IF NOT FOUND THEN
    RAISE EXCEPTION 'no finding %', p_finding_id USING ERRCODE = 'DT005';
  END IF;

  IF p_evidence IS NULL OR jsonb_typeof(p_evidence) <> 'object' THEN
    RAISE EXCEPTION 'evidence must be a JSON object' USING ERRCODE = 'DT005';
  END IF;

  SELECT r.to_status INTO v_current
    FROM finding_resolutions r
    WHERE r.finding_id = p_finding_id
    ORDER BY r.resolution_seq DESC LIMIT 1;
  v_current := COALESCE(v_current, 'OPEN');

  IF v_current IS DISTINCT FROM p_from_status THEN
    RAISE EXCEPTION
      'stale from_status: finding % is %, caller expected %',
      p_finding_id, v_current, p_from_status
      USING ERRCODE = 'DT002';
  END IF;

  IF NOT EXISTS (
    SELECT 1 FROM resolution_status_edges se
    WHERE se.from_status = p_from_status AND se.to_status = p_to_status
  ) THEN
    RAISE EXCEPTION 'illegal resolution edge % -> % (RFC-002 §3.3)',
      p_from_status, p_to_status USING ERRCODE = 'DT004';
  END IF;

  IF p_to_status IN ('COMPENSATED','REDISPATCHED','ACCEPTED_AS_IS','ESCALATED_HUMAN')
     AND NOT EXISTS (
       SELECT 1 FROM resolution_actions ra
       WHERE ra.classification = v_classification AND ra.action = p_to_status
     )
  THEN
    RAISE EXCEPTION 'illegal action % for classification % (RFC-002 §3.3)',
      p_to_status, v_classification USING ERRCODE = 'DT004';
  END IF;

  INSERT INTO finding_resolutions (finding_id, from_status, to_status, evidence, actor)
    VALUES (p_finding_id, p_from_status, p_to_status, p_evidence, p_actor)
    RETURNING resolution_seq INTO v_seq;
  RETURN v_seq;
END $$;
