-- Detent ledger migration 0001 — application role.
-- Plain SQL per ADR-0013; runner per ADR-0022 (proposed). Roles are
-- cluster-wide: guarded for idempotence across template-database rebuilds.
--
-- detent_app is the application role (RFC-002 §2.1/§2.3): INSERT/SELECT on
-- evidence tables only, NO direct write on lifecycle tables, UPDATE/DELETE on
-- no fact table. Grants are per-database and live in 0004_grants.sql.
-- LOGIN without password: local trust-auth dev/test container only; real
-- deployments set credentials out-of-band (never in the repo).

DO $$
BEGIN
  IF NOT EXISTS (SELECT 1 FROM pg_roles WHERE rolname = 'detent_app') THEN
    CREATE ROLE detent_app LOGIN;
  END IF;
END $$;
