-- Irrevon ledger migration 0005 — SELECT-only role for the loopback read
-- surface (`irrevon serve`). Grants only; no shape change (plain SQL per
-- ADR-0013; runner per ADR-0022). Role creation is cluster-wide and guarded
-- for idempotence across template-database rebuilds, exactly like 0001.
--
-- irrevon_read is the second of three independent read-only layers (the HTTP
-- handler is GET/HEAD-only; every serve session additionally opens with
-- default_transaction_read_only=on). Deliberately absent from this file:
-- INSERT/UPDATE/DELETE anywhere; EXECUTE on the locked transition functions
-- (ledger_open_execution / ledger_transition / ledger_attach_finding /
-- ledger_resolve); sequence usage. 0004 revoked PUBLIC's function EXECUTE, so
-- granting nothing here means irrevon_read cannot call them.
-- LOGIN without password: local trust-auth dev/test container only, as 0001;
-- real deployments set credentials out-of-band (never in the repo).

DO $$
BEGIN
  IF NOT EXISTS (SELECT 1 FROM pg_roles WHERE rolname = 'irrevon_read') THEN
    CREATE ROLE irrevon_read LOGIN;
  END IF;
END $$;

-- Defense in depth at the role level: every session this role opens defaults
-- to read-only transactions (the serve connection factory ALSO forces it per
-- connection; a future grant mistake still cannot write without an explicit,
-- grep-able SET TRANSACTION READ WRITE).
ALTER ROLE irrevon_read SET default_transaction_read_only = on;

GRANT USAGE ON SCHEMA public TO irrevon_read;
GRANT SELECT ON ALL TABLES IN SCHEMA public TO irrevon_read;
ALTER DEFAULT PRIVILEGES IN SCHEMA public GRANT SELECT ON TABLES TO irrevon_read;
