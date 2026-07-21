import { useQuery } from "@tanstack/react-query";
import { apiGet } from "@/shared/api/client";
import { effectsSearchToParams, type EffectsSearch } from "@/shared/api/filters";
import { queryKeys } from "@/shared/api/query-keys";
import type { EffectListItem, EffectsEnvelope, InspectPayload } from "@/shared/api/types";

export function useEffectsQuery(search: EffectsSearch) {
  // `inspect` is docked-inspector UI state, not a Q1 filter — it must not
  // fragment the cache or reach the request.
  const { inspect: _inspect, ...filters } = search;
  return useQuery({
    queryKey: queryKeys.effects(filters),
    queryFn: () => {
      const params = effectsSearchToParams(filters).toString();
      return apiGet<EffectsEnvelope>(`/api/v1/effects${params ? `?${params}` : ""}`);
    },
  });
}

export function useEffectItem(effectId: string) {
  return useQuery({
    queryKey: queryKeys.effectRecord(effectId),
    queryFn: () =>
      apiGet<{ schema_version: string } & EffectListItem>(`/api/v1/effects/${effectId}`),
  });
}

export function useEffectInspect(effectId: string) {
  return useQuery({
    queryKey: queryKeys.effectInspect(effectId),
    queryFn: () => apiGet<InspectPayload>(`/api/v1/effects/${effectId}/inspect`),
  });
}
