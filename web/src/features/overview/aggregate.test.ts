import { describe, expect, it } from "vitest";
import type { EffectsEnvelope, FindingsEnvelope } from "@/shared/api/types";
import {
  aggregateEffects,
  aggregateResolutions,
  latestAsOf,
  summarizeDoctor,
} from "./aggregate";

function effectsEnvelope(
  records: { lifecycle: string; adapter: string; effectClass: string; cls?: string }[],
  hasMore = false,
): EffectsEnvelope {
  return {
    schema_version: "1",
    data: records.map((r, i) => ({
      record: {
        effect_id: String(i).padStart(64, "0"),
        lifecycle: r.lifecycle,
        adapter_id: r.adapter,
        effect_class: r.effectClass,
      } as unknown as EffectsEnvelope["data"][number]["record"],
      classification: (r.cls ?? "UNRECONCILED") as "UNRECONCILED",
      finding: null,
    })),
    has_more: hasMore,
    next_cursor: hasMore ? "next" : null,
    as_of: "2026-07-21T10:37:48.648823Z",
  };
}

describe("aggregateEffects", () => {
  it("counts each dimension independently over a complete snapshot", () => {
    const agg = aggregateEffects(
      effectsEnvelope([
        { lifecycle: "AMBIGUOUS", adapter: "refdest-c2", effectClass: "REVERSIBLE" },
        { lifecycle: "PERSISTED", adapter: "refdest-c2", effectClass: "IRREVERSIBLE" },
        {
          lifecycle: "SETTLED_COMMITTED",
          adapter: "refdest-c2",
          effectClass: "IRREVERSIBLE",
          cls: "CONFIRMED_UNIQUE",
        },
      ]),
    );
    expect(agg.complete).toBe(true);
    expect(agg.total).toBe(3);
    // Enum order preserved (ratified order), only present values listed.
    expect(agg.byLifecycle).toEqual([
      { value: "PERSISTED", count: 1 },
      { value: "SETTLED_COMMITTED", count: 1 },
      { value: "AMBIGUOUS", count: 1 },
    ]);
    expect(agg.byClassification).toEqual([
      { value: "UNRECONCILED", count: 2 },
      { value: "CONFIRMED_UNIQUE", count: 1 },
    ]);
    expect(agg.byAdapter).toEqual([{ value: "refdest-c2", count: 3 }]);
    expect(agg.byEffectClass).toEqual([
      { value: "IRREVERSIBLE", count: 2 },
      { value: "REVERSIBLE", count: 1 },
    ]);
    expect(agg.byLifecycle.reduce((sum, row) => sum + row.count, 0)).toBe(agg.total);
  });

  it("refuses to count a partial snapshot", () => {
    const agg = aggregateEffects(
      effectsEnvelope(
        [{ lifecycle: "PERSISTED", adapter: "a", effectClass: "IDEMPOTENT" }],
        true,
      ),
    );
    expect(agg.complete).toBe(false);
    expect(agg.byLifecycle).toEqual([]);
  });

  it("keeps unknown enum values verbatim, appended after known order", () => {
    const agg = aggregateEffects(
      effectsEnvelope([
        { lifecycle: "NOT_A_STATE", adapter: "a", effectClass: "IDEMPOTENT" },
        { lifecycle: "PERSISTED", adapter: "a", effectClass: "IDEMPOTENT" },
      ]),
    );
    expect(agg.byLifecycle).toEqual([
      { value: "PERSISTED", count: 1 },
      { value: "NOT_A_STATE", count: 1 },
    ]);
  });
});

describe("aggregateResolutions", () => {
  it("counts by resolution status and refuses partial envelopes", () => {
    const envelope = {
      schema_version: "1",
      data: [
        { resolution: { status: "OPEN" } },
        { resolution: { status: "OPEN" } },
        { resolution: { status: "CLOSED" } },
      ],
      has_more: false,
      next_cursor: null,
      as_of: "2026-07-21T10:37:48Z",
    } as unknown as FindingsEnvelope;
    expect(aggregateResolutions(envelope).byStatus).toEqual([
      { value: "OPEN", count: 2 },
      { value: "CLOSED", count: 1 },
    ]);
    expect(aggregateResolutions({ ...envelope, has_more: true }).complete).toBe(false);
  });
});

describe("summarizeDoctor", () => {
  it("counts exact statuses and surfaces unrecognized ones separately", () => {
    expect(
      summarizeDoctor([
        { status: "ok" },
        { status: "ok" },
        { status: "warn" },
        { status: "fail" },
        { status: "mystery" },
      ]),
    ).toEqual({ ok: 2, warn: 1, fail: 1, other: 1 });
  });
});

describe("latestAsOf", () => {
  it("is only the maximum of present source values", () => {
    expect(latestAsOf(["2026-07-21T10:00:00Z", undefined, "2026-07-21T11:00:00Z"])).toBe(
      "2026-07-21T11:00:00Z",
    );
    expect(latestAsOf([undefined, undefined])).toBeNull();
  });
});
