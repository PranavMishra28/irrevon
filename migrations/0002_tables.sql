-- Detent ledger migration 0002 — tables, constraints, append-only enforcement,
-- ratified state tables as seed data, derived views.
--
-- Source of truth: docs/rfc-002-engine-design.md §2.2 (DDL), §3 (state tables —
-- the seed rows below are validated against src/detent/ledger/statetable.py by
-- tests/integration/test_state_seed.py; the Python module and RFC §3 govern).
-- Discipline (§2.1): text + CHECK (not enums); timestamptz everywhere; the DB
-- clock is the single time authority; corrections are new rows.

-- ── Append-only enforcement (defense layer 1: triggers; layer 2: grants) ─────

CREATE FUNCTION detent_no_rewrite() RETURNS trigger
LANGUAGE plpgsql AS $$
BEGIN
  RAISE EXCEPTION 'ledger is append-only: % on % is forbidden (RFC-002 §2.1)',
    TG_OP, TG_TABLE_NAME
    USING ERRCODE = 'raise_exception';
END $$;

-- ── Ratified state tables (RFC-002 §3), seeded — SELECT-only reference data ──

CREATE TABLE lifecycle_edges (
  from_state text,                          -- NULL = genesis
  to_state   text NOT NULL,
  cause      text NOT NULL,
  actor      text NOT NULL,
  UNIQUE NULLS NOT DISTINCT (from_state, to_state, cause, actor)
);

INSERT INTO lifecycle_edges (from_state, to_state, cause, actor) VALUES
  (NULL,         'INTENDED',          'register',           'registrar'),
  ('INTENDED',   'PERSISTED',         'durable_write',      'registrar'),
  ('INTENDED',   'CANCELLED',         'branch_cancelled',   'registrar'),
  ('PERSISTED',  'DISPATCHED',        'gate_allow',         'gate'),
  ('PERSISTED',  'CANCELLED',         'branch_cancelled',   'gate'),
  ('PERSISTED',  'CANCELLED',         'branch_cancelled',   'human'),
  ('DISPATCHED', 'SETTLED_COMMITTED', 'receipt_ok',         'dispatcher'),
  ('DISPATCHED', 'SETTLED_FAILED',    'receipt_failed',     'dispatcher'),
  ('DISPATCHED', 'AMBIGUOUS',         'receipt_timeout',    'dispatcher'),
  ('DISPATCHED', 'AMBIGUOUS',         'receipt_timeout',    'recovery'),
  ('DISPATCHED', 'AMBIGUOUS',         'receipt_lost',       'dispatcher'),
  ('DISPATCHED', 'AMBIGUOUS',         'receipt_lost',       'recovery'),
  ('AMBIGUOUS',  'SETTLED_COMMITTED', 'reconciled_present', 'reconciler'),
  ('AMBIGUOUS',  'SETTLED_COMMITTED', 'reconciled_present', 'recovery'),
  ('AMBIGUOUS',  'SETTLED_COMMITTED', 'reconciled_present', 'human'),
  ('AMBIGUOUS',  'SETTLED_COMMITTED', 'replay_ok',          'reconciler'),
  ('AMBIGUOUS',  'SETTLED_COMMITTED', 'replay_ok',          'recovery'),
  ('AMBIGUOUS',  'SETTLED_COMMITTED', 'replay_ok',          'human'),
  ('AMBIGUOUS',  'SETTLED_FAILED',    'reconciled_absent',  'reconciler'),
  ('AMBIGUOUS',  'SETTLED_FAILED',    'reconciled_absent',  'recovery'),
  ('AMBIGUOUS',  'SETTLED_FAILED',    'reconciled_absent',  'human'),
  ('AMBIGUOUS',  'SETTLED_FAILED',    'replay_failed',      'reconciler'),
  ('AMBIGUOUS',  'SETTLED_FAILED',    'replay_failed',      'recovery'),
  ('AMBIGUOUS',  'SETTLED_FAILED',    'replay_failed',      'human');

CREATE TABLE classification_attachments (
  frontier       text NOT NULL,
  classification text NOT NULL,
  UNIQUE (frontier, classification)
);

INSERT INTO classification_attachments (frontier, classification) VALUES
  ('SETTLED_COMMITTED', 'CONFIRMED_UNIQUE'),
  ('SETTLED_COMMITTED', 'DUPLICATE'),
  ('SETTLED_COMMITTED', 'CONTRADICTED'),
  ('SETTLED_FAILED',    'DUPLICATE'),
  ('SETTLED_FAILED',    'LOST'),
  ('SETTLED_FAILED',    'CONTRADICTED');

CREATE TABLE resolution_actions (
  classification text NOT NULL,
  action         text NOT NULL,
  UNIQUE (classification, action)
);

INSERT INTO resolution_actions (classification, action) VALUES
  ('CONFIRMED_UNIQUE', 'ACCEPTED_AS_IS'),
  ('DUPLICATE',        'COMPENSATED'),
  ('DUPLICATE',        'ACCEPTED_AS_IS'),
  ('DUPLICATE',        'ESCALATED_HUMAN'),
  ('LOST',             'REDISPATCHED'),
  ('LOST',             'ACCEPTED_AS_IS'),
  ('LOST',             'ESCALATED_HUMAN'),
  ('ORPHANED',         'COMPENSATED'),
  ('ORPHANED',         'ACCEPTED_AS_IS'),
  ('ORPHANED',         'ESCALATED_HUMAN'),
  ('CONTRADICTED',     'COMPENSATED'),
  ('CONTRADICTED',     'ACCEPTED_AS_IS'),
  ('CONTRADICTED',     'ESCALATED_HUMAN');

CREATE TABLE resolution_status_edges (
  from_status text NOT NULL,
  to_status   text NOT NULL,
  UNIQUE (from_status, to_status)
);

INSERT INTO resolution_status_edges (from_status, to_status) VALUES
  ('OPEN', 'COMPENSATED'),
  ('OPEN', 'REDISPATCHED'),
  ('OPEN', 'ACCEPTED_AS_IS'),
  ('OPEN', 'ESCALATED_HUMAN'),
  ('ESCALATED_HUMAN', 'COMPENSATED'),
  ('ESCALATED_HUMAN', 'REDISPATCHED'),
  ('ESCALATED_HUMAN', 'ACCEPTED_AS_IS'),
  ('COMPENSATED',    'CLOSED'),
  ('REDISPATCHED',   'CLOSED'),
  ('ACCEPTED_AS_IS', 'CLOSED');

-- ── Core tables (RFC-002 §2.2 DDL) ───────────────────────────────────────────

CREATE TABLE effect_records (
  effect_id           text PRIMARY KEY CHECK (effect_id ~ '^[0-9a-f]{64}$'),
  effect_type         text NOT NULL,
  effect_class        text NOT NULL CHECK (effect_class IN
                        ('IDEMPOTENT','REVERSIBLE','COMPENSABLE','IRREVERSIBLE')),
  scope               text NOT NULL,
  stable_ids          jsonb NOT NULL,
  adapter_id          text NOT NULL,             -- ADR-0019; C1 B1/M5
  declaration_digest  text NOT NULL,             -- declaration in force at registration
  parameters_digest   text NOT NULL,             -- canonical digest of dispatchable payload
  contract_canonical  bytea NOT NULL,            -- exact JCS bytes hashed into effect_id
  branch_ref          text,
  event_time          timestamptz,
  created_at          timestamptz NOT NULL DEFAULT now()
);

CREATE TABLE parameter_variants (
  variant_id        bigint GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
  effect_id         text NOT NULL REFERENCES effect_records(effect_id),
  parameters_digest text NOT NULL,
  event_time        timestamptz,
  recorded_at       timestamptz NOT NULL DEFAULT now()
);
CREATE INDEX parameter_variants_effect ON parameter_variants (effect_id);

CREATE TABLE effect_executions (
  execution_id  bigint GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
  effect_id     text    NOT NULL REFERENCES effect_records(effect_id),
  step          integer NOT NULL CHECK (step >= 0),
  operation_id  text    NOT NULL,
  opened_by     text    NOT NULL CHECK (opened_by IN
                  ('register','retry_after_failure','resolve_redispatch')),
  created_at    timestamptz NOT NULL DEFAULT now(),
  UNIQUE (effect_id, step), UNIQUE (operation_id),
  CHECK (operation_id = effect_id || ':' || step::text)
);

CREATE TABLE effect_transitions (          -- INSERT only via ledger_transition() (§2.3)
  transition_seq bigint GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
  execution_id   bigint NOT NULL REFERENCES effect_executions(execution_id),
  from_state     text,                     -- NULL = genesis
  to_state       text NOT NULL,
  cause          text NOT NULL,            -- closed set, §3.1
  actor          text NOT NULL CHECK (actor IN
                   ('registrar','gate','dispatcher','reconciler','recovery','human')),
  evidence       jsonb NOT NULL,           -- probe/receipt/decision ids + digests only
  created_at     timestamptz NOT NULL DEFAULT now(),
  UNIQUE NULLS NOT DISTINCT (execution_id, from_state)   -- defense in depth, not the enforcement
);

CREATE TABLE scope_slots (                 -- the (scope, effect_type) serialization unit
  scope       text NOT NULL,
  effect_type text NOT NULL,
  created_at  timestamptz NOT NULL DEFAULT now(),
  PRIMARY KEY (scope, effect_type)
);

CREATE TABLE gate_decisions (
  decision_id  bigint GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
  effect_id    text   NOT NULL REFERENCES effect_records(effect_id),
  execution_id bigint REFERENCES effect_executions(execution_id),
  variant      text   NOT NULL CHECK (variant IN
                 ('dispatch','recovery_redispatch','resolve_redispatch','retry_after_failure')),
  outcome      text   NOT NULL CHECK (outcome IN ('ALLOW','DENY')),
  deny_check   text   CHECK (deny_check IN ('deny_list','authority','branch_lineage','dedup')),
  checks       jsonb  NOT NULL,            -- ordered check list + input digests
  evidence     jsonb  NOT NULL,
  created_at   timestamptz NOT NULL DEFAULT now(),
  CHECK ((outcome = 'DENY') = (deny_check IS NOT NULL))
);
CREATE INDEX gate_decisions_effect ON gate_decisions (effect_id);

CREATE TABLE dispatch_attempts (
  attempt_id       bigint GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
  execution_id     bigint  NOT NULL REFERENCES effect_executions(execution_id),
  attempt_no       integer NOT NULL CHECK (attempt_no >= 1),
  kind             text    NOT NULL CHECK (kind IN
                     ('primary','recovery_redispatch','c1_replay_probe')),
  adapter_id       text    NOT NULL,
  declaration_digest text  NOT NULL,       -- declaration version used for this attempt (C1 M17)
  idempotency_key  text    NOT NULL,       -- derived ONLY from operation_id
  request_digest   text    NOT NULL,
  gate_decision_id bigint  NOT NULL REFERENCES gate_decisions(decision_id),
  claimed_at       timestamptz NOT NULL DEFAULT now(),
  UNIQUE (execution_id, attempt_no)
);

CREATE TABLE dispatch_receipts (
  receipt_id        bigint GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
  attempt_id        bigint NOT NULL UNIQUE REFERENCES dispatch_attempts(attempt_id),
  transport_outcome text NOT NULL CHECK (transport_outcome IN ('OK','FAILED','TIMEOUT','LOST')),
  failure_kind      text CHECK (failure_kind IN ('TERMINAL','RETRYABLE')),
  destination_ref   text,
  response_digest   text,
  evidence          jsonb NOT NULL,
  recorded_by       text NOT NULL CHECK (recorded_by IN ('dispatcher','reconciler','recovery')),
  recorded_at       timestamptz NOT NULL DEFAULT now(),
  CHECK ((transport_outcome = 'FAILED') = (failure_kind IS NOT NULL))
);

CREATE TABLE late_responses (
  late_id        bigint GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
  attempt_id     bigint NOT NULL REFERENCES dispatch_attempts(attempt_id),
  transport_outcome text NOT NULL CHECK (transport_outcome IN ('OK','FAILED','TIMEOUT','LOST')),
  destination_ref text,
  response_digest text,
  evidence       jsonb NOT NULL,
  contradicts_settle boolean NOT NULL DEFAULT false,  -- enqueues an audit reconcile (§5.1)
  recorded_at    timestamptz NOT NULL DEFAULT now()
);

CREATE TABLE status_probes (
  probe_id        bigint GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
  execution_id    bigint NOT NULL REFERENCES effect_executions(execution_id),
  adapter_id      text  NOT NULL,
  declaration_digest text NOT NULL,
  probe_kind      text  NOT NULL CHECK (probe_kind IN ('reconcile_open','audit','sweep')),
  query_keys      jsonb NOT NULL,
  result          text  NOT NULL CHECK (result IN ('PRESENT','ABSENT','INDETERMINATE')),
  n_found         integer,
  destination_refs jsonb,
  response_digest text,
  queried_at      timestamptz NOT NULL,
  recorded_at     timestamptz NOT NULL DEFAULT now(),
  CHECK ((result = 'PRESENT') = (n_found IS NOT NULL AND n_found >= 1)),
  CHECK (result <> 'ABSENT' OR n_found = 0)
);
CREATE INDEX status_probes_execution ON status_probes (execution_id);

CREATE TABLE findings (                    -- INSERT only via ledger_attach_finding()
  finding_id      bigint GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
  effect_id       text REFERENCES effect_records(effect_id),
  adapter_id      text NOT NULL,
  destination_ref text,
  classification  text NOT NULL CHECK (classification IN
                    ('CONFIRMED_UNIQUE','DUPLICATE','LOST','ORPHANED','CONTRADICTED')),
  excess_effect_count integer,             -- DUPLICATE: destination effects beyond the first
  evidence        jsonb NOT NULL,          -- metadata + digests only (§0 rule 5)
  evidence_digest text NOT NULL,
  created_by      text NOT NULL CHECK (created_by IN ('reconciler','recovery','sweep','human')),
  created_at      timestamptz NOT NULL DEFAULT now(),
  CHECK ((classification = 'ORPHANED') = (effect_id IS NULL)),
  CHECK (effect_id IS NOT NULL OR destination_ref IS NOT NULL),
  -- NULL-strict: a NULL excess on a DUPLICATE must fail, not vacuously pass.
  CHECK (classification <> 'DUPLICATE'
         OR (excess_effect_count IS NOT NULL AND excess_effect_count >= 1))
);
CREATE UNIQUE INDEX findings_one_orphan_per_ref ON findings (adapter_id, destination_ref)
  WHERE classification = 'ORPHANED';       -- destination identity in the key (C1 M5)
CREATE INDEX findings_effect ON findings (effect_id);

CREATE TABLE finding_resolutions (         -- INSERT only via ledger_resolve() (§2.3)
  resolution_seq bigint GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
  finding_id   bigint NOT NULL REFERENCES findings(finding_id),
  from_status  text NOT NULL,
  to_status    text NOT NULL,
  evidence     jsonb NOT NULL,
  actor        text NOT NULL CHECK (actor IN ('human','policy_auto','recovery','system')),
  created_at   timestamptz NOT NULL DEFAULT now(),
  UNIQUE (finding_id, from_status)
  -- legality of (from_status, to_status) enforced by ledger_resolve per §3.3
);

-- ── Adjunct tables (authority model, branches, deny-list, journals — §2.2) ───

CREATE TABLE authorities (
  authority_id  bigint GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
  authority_ref text NOT NULL,
  scope         text NOT NULL,
  stamped_at    timestamptz NOT NULL,
  expires_at    timestamptz,               -- issuer expiry; NULL falls back to policy max_age
  created_at    timestamptz NOT NULL DEFAULT now()
);

CREATE TABLE effect_authorities (
  link_id      bigint GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
  effect_id    text   NOT NULL REFERENCES effect_records(effect_id),
  authority_id bigint NOT NULL REFERENCES authorities(authority_id),
  created_at   timestamptz NOT NULL DEFAULT now()
);
CREATE INDEX effect_authorities_effect ON effect_authorities (effect_id);

CREATE TABLE authority_policies (
  policy_id     bigint GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
  scope_pattern text NOT NULL,             -- '*' = default policy
  max_age       interval NOT NULL,
  created_at    timestamptz NOT NULL DEFAULT now()
);
-- Default authority freshness policy (tunable [DD]; expiry = issuer expires_at,
-- else stamped_at + policy max_age, else deny — RFC-002 §2.2 authority model).
INSERT INTO authority_policies (scope_pattern, max_age) VALUES ('*', interval '24 hours');

CREATE TABLE branch_cancellations (
  branch_ref   text PRIMARY KEY,
  reason       text NOT NULL,
  cancelled_at timestamptz NOT NULL DEFAULT now()
);

CREATE TABLE deny_entries (
  deny_id      bigint GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
  effect_class text,
  effect_type  text,
  scope        text,
  reason       text NOT NULL,
  created_at   timestamptz NOT NULL DEFAULT now(),
  CHECK (effect_class IS NOT NULL OR effect_type IS NOT NULL OR scope IS NOT NULL)
);

CREATE TABLE deny_lifts (
  lift_id    bigint GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
  deny_id    bigint NOT NULL UNIQUE REFERENCES deny_entries(deny_id),
  lifted_at  timestamptz NOT NULL DEFAULT now()
);

CREATE TABLE sweep_runs (
  run_id      bigint GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
  adapter_id  text NOT NULL,
  window_from timestamptz NOT NULL,
  window_to   timestamptz NOT NULL,
  listed      integer NOT NULL,
  matched     integer NOT NULL,
  recorded_at timestamptz NOT NULL DEFAULT now()
);

CREATE TABLE sweep_sightings (
  sighting_id     bigint GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
  run_id          bigint NOT NULL REFERENCES sweep_runs(run_id),
  adapter_id      text NOT NULL,
  destination_ref text NOT NULL,
  payload_digest  text NOT NULL,
  matched_effect  text REFERENCES effect_records(effect_id),
  match_path      text,                    -- client_ref | destination_ref | queryable_keys | open_attempt
  sighted_at      timestamptz NOT NULL DEFAULT now(),
  UNIQUE (run_id, adapter_id, destination_ref)   -- re-listing within a run is idempotent (C1 N2)
);

CREATE TABLE recovery_runs (
  run_id       bigint GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
  scanned      integer NOT NULL,
  adjudicated  integer NOT NULL,
  parked       integer NOT NULL,
  queued_redispatches integer NOT NULL,
  recorded_at  timestamptz NOT NULL DEFAULT now()
);

-- ── Append-only triggers on every fact table ─────────────────────────────────

DO $$
DECLARE t text;
BEGIN
  FOREACH t IN ARRAY ARRAY[
    'effect_records','parameter_variants','effect_executions','effect_transitions',
    'scope_slots','gate_decisions','dispatch_attempts','dispatch_receipts',
    'late_responses','status_probes','findings','finding_resolutions',
    'authorities','effect_authorities','authority_policies','branch_cancellations',
    'deny_entries','deny_lifts','sweep_runs','sweep_sightings','recovery_runs',
    'lifecycle_edges','classification_attachments','resolution_actions',
    'resolution_status_edges'
  ] LOOP
    EXECUTE format(
      'CREATE TRIGGER %I BEFORE UPDATE OR DELETE ON %I
         FOR EACH STATEMENT EXECUTE FUNCTION detent_no_rewrite()',
      t || '_append_only', t);
  END LOOP;
END $$;

-- ── Derived views (frontier + open attempts; §2.2 note) ──────────────────────

CREATE VIEW execution_frontiers AS
SELECT e.execution_id,
       e.effect_id,
       e.step,
       e.operation_id,
       e.opened_by,
       t.to_state AS frontier,
       t.transition_seq AS frontier_seq
FROM effect_executions e
JOIN LATERAL (
  SELECT to_state, transition_seq
  FROM effect_transitions
  WHERE execution_id = e.execution_id
  ORDER BY transition_seq DESC
  LIMIT 1
) t ON true;

CREATE VIEW effect_frontiers AS
SELECT DISTINCT ON (f.effect_id)
       f.effect_id, f.execution_id, f.step, f.operation_id, f.frontier
FROM execution_frontiers f
ORDER BY f.effect_id, f.step DESC;

CREATE VIEW open_attempts AS
SELECT a.attempt_id, a.execution_id, a.attempt_no, a.kind, a.adapter_id,
       a.idempotency_key, a.claimed_at,
       e.effect_id, r.scope, r.effect_type
FROM dispatch_attempts a
JOIN effect_executions e ON e.execution_id = a.execution_id
JOIN effect_records r ON r.effect_id = e.effect_id
WHERE NOT EXISTS (
  SELECT 1 FROM dispatch_receipts rc WHERE rc.attempt_id = a.attempt_id
);
