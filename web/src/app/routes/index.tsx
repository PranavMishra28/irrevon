import { createFileRoute, redirect } from "@tanstack/react-router";

/**
 * Deterministic landing (BRIEF §3.3):
 * 1. virgin ledger / explicit mock review → /learn/start
 * 2. live connection unavailable with no last-good snapshot → /health
 * 3. otherwise → /effects
 * Until the Q1 contract exists there is no record source, so the honest
 * landing is Start Here in every build.
 */
export const Route = createFileRoute("/")({
  beforeLoad: () => {
    throw redirect({ to: "/learn/start" });
  },
});
