import { readFileSync, readdirSync } from "node:fs";
import { join } from "node:path";
import { describe, expect, it } from "vitest";
import type { InspectPayload } from "@/shared/api/types";
import {
  RELATIONS,
  buildEffectGraph,
  resolveEvidencePath,
  type BuildInput,
  type GraphModel,
} from "./model";
import { layoutGraph } from "./layout";
import { truncateGraphValue } from "./render-utils";

const FIXTURE_DIR = join(import.meta.dirname, "../../../fixtures/canonical/inspect");
const FIXTURES = readdirSync(FIXTURE_DIR).filter((name) => name.endsWith(".json"));

function loadFixture(name: string): InspectPayload {
  return JSON.parse(readFileSync(join(FIXTURE_DIR, name), "utf8")) as InspectPayload;
}

/** Deep-clone with object keys re-inserted in reverse order. */
function permuteKeys(value: unknown): unknown {
  if (Array.isArray(value)) return value.map(permuteKeys);
  if (value !== null && typeof value === "object") {
    const entries = Object.entries(value as Record<string, unknown>).reverse();
    const out: Record<string, unknown> = {};
    for (const [k, v] of entries) out[k] = permuteKeys(v);
    return out;
  }
  return value;
}

describe("buildEffectGraph — canonical fixtures", () => {
  it("covers all seven canonical inspect fixtures", () => {
    expect(FIXTURES).toHaveLength(7);
  });

  for (const name of FIXTURES) {
    it(`produces a deterministic snapshot for ${name.slice(0, 12)}`, () => {
      const model = buildEffectGraph({ inspect: loadFixture(name) });
      expect({
        effectId: model.effectId,
        integrityFailure: model.integrityFailure,
        notes: model.notes,
        nodes: model.nodes.map((n) => ({
          id: n.id,
          kind: n.kind,
          primary: n.primary,
          rank: n.rank,
          lateral: n.lateral,
          frame: n.frame,
          hatched: n.hatched ?? false,
        })),
        edges: model.edges.map((e) => ({
          id: e.id,
          from: e.from,
          to: e.to,
          relation: e.relation,
          stroke: e.stroke,
          evidencePath: e.evidencePath,
        })),
        annotations: model.annotations.map((a) => ({ id: a.id, kind: a.kind })),
      }).toMatchSnapshot();
    });

    it(`every edge's evidencePath resolves for ${name.slice(0, 12)}`, () => {
      const input: BuildInput = { inspect: loadFixture(name) };
      const model = buildEffectGraph(input);
      for (const edge of model.edges) {
        const resolved = resolveEvidencePath(input, edge.evidencePath);
        expect(resolved, `${edge.id} → ${edge.evidencePath}`).not.toBeUndefined();
      }
      // Node fact citations resolve too (I2).
      for (const node of model.nodes) {
        for (const fact of node.facts) {
          expect(
            resolveEvidencePath(input, fact.path),
            `${node.id} fact ${fact.label} → ${fact.path}`,
          ).not.toBeUndefined();
        }
      }
    });

    it(`ordering is invariant under object-key permutation for ${name.slice(0, 12)}`, () => {
      const original = loadFixture(name);
      const permuted = permuteKeys(original) as InspectPayload;
      const a = buildEffectGraph({ inspect: original });
      const b = buildEffectGraph({ inspect: permuted });
      expect(b.nodes.map((n) => n.id)).toEqual(a.nodes.map((n) => n.id));
      expect(b.edges.map((e) => e.id)).toEqual(a.edges.map((e) => e.id));
    });

    it(`uses only the closed relation vocabulary for ${name.slice(0, 12)}`, () => {
      const model = buildEffectGraph({ inspect: loadFixture(name) });
      for (const edge of model.edges) {
        expect(RELATIONS).toContain(edge.relation);
      }
    });
  }
});

describe("buildEffectGraph — invariants", () => {
  const flagship = FIXTURES.find((n) => n.startsWith("0bb7"));
  const persisted = FIXTURES.find((n) => n.startsWith("371a"));
  const ambiguous = FIXTURES.find((n) => n.startsWith("f18a"));

  it("PERSISTED-only case draws no notch: nothing dispatched", () => {
    expect(persisted).toBeDefined();
    const model = buildEffectGraph({ inspect: loadFixture(persisted ?? "") });
    expect(model.annotations.filter((a) => a.kind === "notch")).toHaveLength(0);
    expect(model.nodes.filter((n) => ["attempt", "observation"].includes(n.kind))).toHaveLength(
      0,
    );
  });

  it("flagship carries the notch, a lateral DENY, dedup-cites, and a variant chip", () => {
    expect(flagship).toBeDefined();
    const model = buildEffectGraph({ inspect: loadFixture(flagship ?? "") });
    expect(model.annotations.some((a) => a.kind === "notch")).toBe(true);
    expect(model.annotations.some((a) => a.kind === "crash-seam")).toBe(true);
    const deny = model.nodes.find((n) => n.kind === "gate" && n.lateral);
    expect(deny).toBeDefined();
    expect(model.edges.some((e) => e.relation === "dedup-cites")).toBe(true);
    expect(model.nodes.some((n) => n.kind === "variant")).toBe(true);
    // DENY never crosses the notch: no dispatched-through edge leaves it.
    expect(
      model.edges.filter((e) => e.from === deny?.id && e.relation === "dispatched-through"),
    ).toHaveLength(0);
  });

  it("AMBIGUOUS renders a labeled unknown slot with an interrupted evidence gap", () => {
    expect(ambiguous).toBeDefined();
    const model = buildEffectGraph({ inspect: loadFixture(ambiguous ?? "") });
    const slot = model.nodes.find((n) => n.kind === "unknown-slot");
    expect(slot?.absenceText).toContain("destination state unknown");
    const gap = model.edges.find((e) => e.relation === "evidence-gap");
    expect(gap?.stroke).toBe("interrupted");
    expect(gap?.to).toBe(slot?.id);
  });

  it("unknown enum values become labeled unrecognized nodes, never a known kind", () => {
    const payload = loadFixture(flagship ?? "");
    const mutated = {
      ...payload,
      record: { ...payload.record, lifecycle: "NOT_A_STATE" },
      gate_decisions: payload.gate_decisions.map((d, i) =>
        i === 0 ? { ...d, outcome: "MYSTERY" } : d,
      ),
    } as InspectPayload;
    const model = buildEffectGraph({ inspect: mutated });
    const identity = model.nodes.find((n) => n.kind === "identity");
    expect(identity?.unrecognized).toBe(true);
    const gate = model.nodes.find((n) => n.id === "node:gate:1");
    expect(gate?.unrecognized).toBe(true);
    expect(gate?.primary).toContain("MYSTERY");
  });

  it("integrity mismatch raises the incident flag without normalizing anything", () => {
    const payload = loadFixture(flagship ?? "");
    const mutated = {
      ...payload,
      integrity: { recomputed_intent_id: "f".repeat(64), matches: false },
    } as InspectPayload;
    const model = buildEffectGraph({ inspect: mutated });
    expect(model.integrityFailure).toBe(true);
    expect(model.effectId).toBe(payload.record.effect_id);
  });

  it("empty timeline yields an explicit note, never an invented genesis", () => {
    const payload = loadFixture(persisted ?? "");
    const mutated = { ...payload, timeline: [] } as InspectPayload;
    const model = buildEffectGraph({ inspect: mutated });
    expect(model.notes).toContain("no transitions recorded");
    expect(model.nodes.filter((n) => n.kind === "execution")).toHaveLength(0);
  });
});

describe("layout — integer coordinates and orientation invariants", () => {
  function assertIntegerLayout(model: GraphModel) {
    for (const orientation of ["horizontal", "vertical"] as const) {
      const layout = layoutGraph(model, orientation);
      for (const node of layout.nodes) {
        for (const value of [node.x, node.y, node.w, node.h]) {
          expect(Number.isInteger(value), `${node.id} ${orientation}`).toBe(true);
        }
      }
      for (const edge of layout.edges) {
        for (const value of [edge.x1, edge.y1, edge.x2, edge.y2]) {
          expect(Number.isInteger(value), `${edge.id} ${orientation}`).toBe(true);
        }
      }
      expect(layout.nodes.map((n) => n.id)).toEqual(model.nodes.map((n) => n.id));
      // No overlap between node boxes.
      for (let i = 0; i < layout.nodes.length; i += 1) {
        for (let j = i + 1; j < layout.nodes.length; j += 1) {
          const a = layout.nodes[i];
          const b = layout.nodes[j];
          if (!a || !b) continue;
          const overlap =
            a.x < b.x + b.w && b.x < a.x + a.w && a.y < b.y + b.h && b.y < a.y + a.h;
          expect(overlap, `${a.id} overlaps ${b.id} (${orientation})`).toBe(false);
        }
      }
    }
  }

  for (const name of FIXTURES) {
    it(`layout invariants hold for ${name.slice(0, 12)}`, () => {
      assertIntegerLayout(buildEffectGraph({ inspect: loadFixture(name) }));
    });
  }

  it("30-node stress model stays integer-stable with no overlaps", () => {
    const base = loadFixture(FIXTURES.find((n) => n.startsWith("0bb7")) ?? "");
    // Synthesize extra executions/receipts/probes from the real records.
    const stress = {
      ...base,
      timeline: [
        ...base.timeline,
        ...Array.from({ length: 6 }, (_, i) => ({
          ...(base.timeline[0] ?? {}),
          transition_seq: 100 + i,
          step: i + 1,
          operation_id: `${base.record.effect_id}:${i + 1}`,
          created_at: `2026-07-21 11:0${i}:00+00:00`,
        })),
      ],
      receipts: [
        ...base.receipts,
        ...Array.from({ length: 8 }, (_, i) => ({
          ...(base.receipts[0] ?? {}),
          receipt_id: 100 + i,
          attempt_no: i + 2,
          operation_id: `${base.record.effect_id}:${(i % 6) + 1}`,
          recorded_at: `2026-07-21 11:1${i % 10}:00+00:00`,
        })),
      ],
      probes: [
        ...base.probes,
        ...Array.from({ length: 8 }, (_, i) => ({
          ...(base.probes[0] ?? {}),
          probe_id: 100 + i,
          queried_at: `2026-07-21 11:2${i % 10}:00+00:00`,
        })),
      ],
    } as InspectPayload;
    const model = buildEffectGraph({ inspect: stress });
    expect(model.nodes.length).toBeGreaterThanOrEqual(30);
    assertIntegerLayout(model);
  });
});

describe("truncation contract", () => {
  it("effect ids keep the leading prefix (12 hex), never middle-truncated", () => {
    const id = "0bb7e8d64711e0cc5ec277fb9bb64d3d321fdd53dd92b8ebb1752fde822785f5";
    expect(truncateGraphValue(id)).toBe("0bb7e8d64711…");
  });

  it("operation ids keep the full :step visible", () => {
    const id = `${"a".repeat(64)}:3`;
    expect(truncateGraphValue(id)).toBe(`${"a".repeat(12)}…:3`);
  });

  it("digests use head-tail 8…4", () => {
    const digest = `sha256:${"1f4a".repeat(16)}`;
    expect(truncateGraphValue(digest)).toBe("sha256:1f4a1f4a…1f4a");
  });

  it("non-identifier values pass through untouched", () => {
    expect(truncateGraphValue("order.create · acme-store/prod")).toBe(
      "order.create · acme-store/prod",
    );
  });
});
