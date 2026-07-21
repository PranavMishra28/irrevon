import type { EffectsEnvelope, FindingsEnvelope } from "@/shared/api/types";
import {
  CLASSIFICATIONS,
  LIFECYCLE_STATES,
  RESOLUTION_STATUSES,
} from "@/shared/contracts/generated/state-model";

/**
 * Overview aggregation (REDESIGN-BRIEF A4): deterministic counts over a
 * COMPLETE served snapshot only. A partial envelope (has_more: true) yields
 * `complete: false` and no counts — a page count is never presented as a
 * total. Counts are grouped independently per dimension; enum dimensions
 * keep ratified enum order, free-string dimensions sort lexically. Unknown
 * enum values are kept verbatim and appended after the known order — never
 * coerced.
 */

export interface CountRow {
  value: string;
  count: number;
}

export interface EffectAggregates {
  complete: boolean;
  total: number;
  byLifecycle: CountRow[];
  byClassification: CountRow[];
  byAdapter: CountRow[];
  byEffectClass: CountRow[];
}

function countBy(values: string[], knownOrder: readonly string[]): CountRow[] {
  const counts = new Map<string, number>();
  for (const value of values) {
    counts.set(value, (counts.get(value) ?? 0) + 1);
  }
  const known = knownOrder
    .filter((value) => counts.has(value))
    .map((value) => ({ value, count: counts.get(value) ?? 0 }));
  const unknown = [...counts.keys()]
    .filter((value) => !knownOrder.includes(value))
    .sort()
    .map((value) => ({ value, count: counts.get(value) ?? 0 }));
  return [...known, ...unknown];
}

function countByString(values: string[]): CountRow[] {
  return countBy(values, [...new Set(values)].sort());
}

export function aggregateEffects(envelope: EffectsEnvelope): EffectAggregates {
  if (envelope.has_more) {
    return {
      complete: false,
      total: envelope.data.length,
      byLifecycle: [],
      byClassification: [],
      byAdapter: [],
      byEffectClass: [],
    };
  }
  const items = envelope.data;
  return {
    complete: true,
    total: items.length,
    byLifecycle: countBy(
      items.map((i) => i.record.lifecycle),
      LIFECYCLE_STATES,
    ),
    byClassification: countBy(
      items.map((i) => i.classification),
      ["UNRECONCILED", ...CLASSIFICATIONS],
    ),
    byAdapter: countByString(items.map((i) => i.record.adapter_id)),
    byEffectClass: countByString(items.map((i) => i.record.effect_class)),
  };
}

export interface ResolutionAggregates {
  complete: boolean;
  total: number;
  byStatus: CountRow[];
}

export function aggregateResolutions(envelope: FindingsEnvelope): ResolutionAggregates {
  if (envelope.has_more) {
    return { complete: false, total: envelope.data.length, byStatus: [] };
  }
  return {
    complete: true,
    total: envelope.data.length,
    byStatus: countBy(
      envelope.data.map((finding) => String(finding.resolution.status)),
      RESOLUTION_STATUSES,
    ),
  };
}

/** Doctor transcript summary: exact ok/warn/fail counts, nothing invented. */
export function summarizeDoctor(checks: { status: string }[]): {
  ok: number;
  warn: number;
  fail: number;
  other: number;
} {
  let ok = 0;
  let warn = 0;
  let fail = 0;
  let other = 0;
  for (const check of checks) {
    if (check.status === "ok") ok += 1;
    else if (check.status === "warn") warn += 1;
    else if (check.status === "fail") fail += 1;
    else other += 1;
  }
  return { ok, warn, fail, other };
}

/**
 * "Latest observed as_of" is ONLY the maximum of the per-source values —
 * differing source timestamps remain individually visible.
 */
export function latestAsOf(asOfs: (string | undefined)[]): string | null {
  const present = asOfs.filter((value): value is string => typeof value === "string");
  if (present.length === 0) return null;
  return present.reduce((a, b) => (a >= b ? a : b));
}
