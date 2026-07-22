import { useQuery } from "@tanstack/react-query";
import { isMockMode } from "@/app/data-mode";
import { apiGet } from "@/shared/api/client";
import { UnsupportedVersionError } from "@/shared/api/errors";
import { queryKeys } from "@/shared/api/query-keys";
import type { DoctorPayload } from "@/shared/api/types";
import type { LiveStatus } from "@/shared/domain/status/live-mode";

/**
 * Live-mode connection status, driven by a poll of /api/v1/health — the
 * only routine poll in the app (serve spec §3.2: refetchInterval 15s,
 * retry 1; the single retry backs off exponentially via react-query's
 * default retryDelay before the query surfaces as errored).
 *
 * States:
 * - connecting: no health response observed yet (no banner — a cold start
 *   must not flash "disconnected" before the first probe lands)
 * - connected: 2xx with a supported schema_version; carries the doctor verdict
 * - disconnected: transport/404/5xx — data stays stale-marked; nothing can
 *   fall back to fixtures because live bundles contain none
 * - unsupported: payload schema_version mismatch — full-surface refusal
 */

export const HEALTH_POLL_INTERVAL_MS = 15_000;

export type { LiveStatus } from "@/shared/domain/status/live-mode";

/** Pure derivation from query facts — unit-tested without a network. */
export function deriveLiveStatus(input: {
  status: "pending" | "error" | "success";
  error: unknown;
  data: DoctorPayload | undefined;
  dataUpdatedAt: number;
}): LiveStatus {
  if (input.error instanceof UnsupportedVersionError) {
    return {
      state: "unsupported",
      observed: input.error.received,
      supported: input.error.supported,
    };
  }
  if (input.status === "error") {
    return {
      state: "disconnected",
      lastUpdatedAt: input.dataUpdatedAt > 0 ? input.dataUpdatedAt : null,
    };
  }
  if (input.status === "success" && input.data) {
    const failingChecks = input.data.checks.filter((c) => c.status === "fail").length;
    return {
      state: "connected",
      doctorOk: failingChecks === 0,
      failingChecks,
      lastUpdatedAt: input.dataUpdatedAt,
    };
  }
  return { state: "connecting" };
}

export function useLiveStatus(): LiveStatus {
  const query = useQuery({
    queryKey: queryKeys.health(),
    queryFn: () => apiGet<DoctorPayload>("/api/v1/health"),
    // Inert in mock builds: the fixture banner is the mock disclosure and
    // no poll may run against MSW.
    enabled: !isMockMode,
    refetchInterval: HEALTH_POLL_INTERVAL_MS,
    refetchIntervalInBackground: false,
    retry: 1,
  });

  if (isMockMode) return { state: "connecting" };

  return deriveLiveStatus({
    status: query.status,
    error: query.error,
    data: query.data,
    dataUpdatedAt: query.dataUpdatedAt,
  });
}
