import type { EffectsSearch } from "./filters";

/** Query keys mirror the read contracts. */
export const queryKeys = {
  effects: (filters: EffectsSearch) => ["effects", filters] as const,
  effectInspect: (effectId: string) => ["effect-inspect", effectId] as const,
  effectRecord: (effectId: string) => ["effect-record", effectId] as const,
  findings: () => ["findings"] as const,
  adapters: () => ["adapters"] as const,
  health: () => ["health"] as const,
  demoArtifact: () => ["demo-artifact"] as const,
};
