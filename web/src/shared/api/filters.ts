import { CLASSIFICATIONS, LIFECYCLE_STATES } from "@/shared/contracts/generated/state-model";
import type { Classification, Lifecycle } from "@/shared/contracts/generated/state-model";

/**
 * Q1 filter model (RFC-002 §9): exact enum filters, URL-backed so every
 * filtered evidence view is a shareable artifact. No fuzzy matching.
 */
export interface EffectsSearch {
  lifecycle?: Lifecycle[];
  classification?: (Classification | "UNRECONCILED")[];
  effect_type?: string;
  cursor?: string;
}

const CLASSIFICATION_FILTERS: readonly string[] = [...CLASSIFICATIONS, "UNRECONCILED"];

function toArray(value: unknown): string[] {
  if (typeof value === "string") return [value];
  if (Array.isArray(value)) return value.filter((v): v is string => typeof v === "string");
  return [];
}

/** Validate raw search params into the typed filter model (unknown values dropped). */
export function parseEffectsSearch(search: Record<string, unknown>): EffectsSearch {
  const out: EffectsSearch = {};
  const lifecycle = toArray(search.lifecycle).filter((v): v is Lifecycle =>
    (LIFECYCLE_STATES as readonly string[]).includes(v),
  );
  if (lifecycle.length > 0) out.lifecycle = lifecycle;
  const classification = toArray(search.classification).filter(
    (v): v is Classification | "UNRECONCILED" => CLASSIFICATION_FILTERS.includes(v),
  );
  if (classification.length > 0) out.classification = classification;
  if (typeof search.effect_type === "string" && search.effect_type !== "") {
    out.effect_type = search.effect_type;
  }
  if (typeof search.cursor === "string" && search.cursor !== "") {
    out.cursor = search.cursor;
  }
  return out;
}

/** Serialize the filter model to Q1 request params, exactly as contracted. */
export function effectsSearchToParams(search: EffectsSearch): URLSearchParams {
  const params = new URLSearchParams();
  for (const value of search.lifecycle ?? []) params.append("lifecycle", value);
  for (const value of search.classification ?? []) params.append("classification", value);
  if (search.effect_type !== undefined) params.set("effect_type", search.effect_type);
  if (search.cursor !== undefined) params.set("cursor", search.cursor);
  return params;
}
