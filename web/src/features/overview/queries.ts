import { useQuery } from "@tanstack/react-query";
import { apiGet } from "@/shared/api/client";
import { queryKeys } from "@/shared/api/query-keys";
import type {
  AdaptersPayload,
  DoctorPayload,
  EffectsEnvelope,
  FindingsEnvelope,
} from "@/shared/api/types";

/** Overview reads the same contracts as their owning surfaces — no new API. */

export function useOverviewEffects() {
  return useQuery({
    queryKey: queryKeys.effects({}),
    queryFn: () => apiGet<EffectsEnvelope>("/api/v1/effects"),
  });
}

export function useOverviewFindings() {
  return useQuery({
    queryKey: queryKeys.findings(),
    queryFn: () => apiGet<FindingsEnvelope>("/api/v1/findings"),
  });
}

export function useOverviewAdapters() {
  return useQuery({
    queryKey: queryKeys.adapters(),
    queryFn: () => apiGet<AdaptersPayload>("/api/v1/adapters"),
  });
}

export function useOverviewDoctor() {
  return useQuery({
    queryKey: queryKeys.health(),
    queryFn: () => apiGet<DoctorPayload>("/api/v1/health"),
  });
}
