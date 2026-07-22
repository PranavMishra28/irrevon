-- Irrevon ledger migration 0004 — privilege separation (RFC-002 §2.1/§2.3).
--
-- irrevon_app: INSERT/SELECT on evidence tables only; NO direct write on
-- lifecycle tables (effect_executions, effect_transitions, findings,
-- finding_resolutions — locked-function-only); UPDATE/DELETE granted to no
-- application role on any fact table. UPDATE on scope_slots/effect_records is
-- granted ONLY because SELECT ... FOR UPDATE requires it for claim-transaction
-- row locking (§5.1); the append-only triggers reject any actual UPDATE.

REVOKE ALL ON ALL TABLES IN SCHEMA public FROM PUBLIC;
REVOKE ALL ON ALL FUNCTIONS IN SCHEMA public FROM PUBLIC;

GRANT USAGE ON SCHEMA public TO irrevon_app;

-- Read everything (incl. the derived views and ratified seed tables).
GRANT SELECT ON ALL TABLES IN SCHEMA public TO irrevon_app;
GRANT SELECT ON execution_frontiers, effect_frontiers, open_attempts TO irrevon_app;

-- Evidence tables: append (INSERT) only.
GRANT INSERT ON
  effect_records, parameter_variants, scope_slots, gate_decisions,
  dispatch_attempts, dispatch_receipts, late_responses, status_probes,
  authorities, effect_authorities, branch_cancellations,
  deny_entries, deny_lifts, sweep_runs, sweep_sightings, recovery_runs
TO irrevon_app;

-- Row-locking privilege only (see header); real UPDATEs raise via trigger.
GRANT UPDATE ON scope_slots, effect_records TO irrevon_app;

-- Identity-column sequences.
GRANT USAGE ON ALL SEQUENCES IN SCHEMA public TO irrevon_app;

-- The locked transition writer (§2.3).
GRANT EXECUTE ON FUNCTION
  ledger_open_execution(text, text),
  ledger_transition(bigint, text, text, text, text, jsonb),
  ledger_attach_finding(text, text, text, text, integer, jsonb, text, text),
  ledger_resolve(bigint, text, text, text, jsonb)
TO irrevon_app;
