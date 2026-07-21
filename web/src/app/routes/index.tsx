import { createFileRoute, redirect } from "@tanstack/react-router";

import { isMockMode } from "@/app/data-mode";

/**
 * Deterministic landing (BRIEF §3.3):
 * 1. virgin ledger → /learn/start
 * 2. live connection unavailable with no last-good snapshot → /health
 * 3. otherwise → /effects
 * Mock builds carry the captured (non-virgin) fixture ledger → Effects;
 * live mode has no ratified read server yet (BI-4) → Health.
 */
export const Route = createFileRoute("/")({
  beforeLoad: () => {
    throw redirect({ to: isMockMode ? "/effects" : "/health" });
  },
});
