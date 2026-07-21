import { describe, expect, it } from "vitest";
import type { ReconciliationFinding } from "@/shared/contracts/generated/reconciliation-finding";
import type { EffectListItem } from "@/shared/api/types";
import { deriveAttention } from "./derive";

const HEX = (n: number) => String(n).padStart(64, "a");

function effect(id: string, lifecycle: string, type = "order.create"): EffectListItem {
  return {
    record: {
      effect_id: id,
      lifecycle,
      effect_type: type,
      scope: "acme-store/prod",
    } as unknown as EffectListItem["record"],
    classification: "UNRECONCILED",
    finding: null,
  };
}

function finding(
  id: string,
  status: string,
  subject: ReconciliationFinding["subject"],
  classification = "LOST",
): ReconciliationFinding {
  return {
    schema_version: "1",
    finding_id: id,
    subject,
    adapter_id: "refdest-c2",
    classification,
    evidence_digest: "sha256:x",
    evidence: { digest: "sha256:x", redaction: "digest_only" },
    created_by: "reconciler",
    created_at: "2026-07-21T10:00:00Z",
    resolution: { status },
  } as unknown as ReconciliationFinding;
}

describe("deriveAttention", () => {
  it("implements exactly the A5 formula: AMBIGUOUS effects UNION open findings", () => {
    const result = deriveAttention({
      effects: [effect(HEX(1), "AMBIGUOUS"), effect(HEX(2), "SETTLED_COMMITTED")],
      findings: [
        finding("fnd_1", "OPEN", { effect_id: HEX(3) }),
        finding("fnd_2", "CLOSED", { effect_id: HEX(4) }),
        finding("fnd_3", "ESCALATED_HUMAN", {
          adapter_id: "refdest-c2",
          destination_ref: "dest_x",
        }),
      ],
      effectsPartial: false,
      findingsPartial: false,
    });
    expect(result.items.map((i) => i.key)).toEqual([
      `effect:${HEX(1)}`,
      `effect:${HEX(3)}`,
      "destination:refdest-c2:dest_x",
    ]);
    expect(result.ambiguousCount).toBe(1);
    expect(result.openFindingCount).toBe(2);
    expect(result.partial).toBe(false);
  });

  it("merges duplicate keys by reason — never scores", () => {
    const result = deriveAttention({
      effects: [effect(HEX(1), "AMBIGUOUS")],
      findings: [finding("fnd_1", "OPEN", { effect_id: HEX(1) })],
      effectsPartial: false,
      findingsPartial: false,
    });
    expect(result.items).toHaveLength(1);
    expect(result.items[0]?.reasons).toHaveLength(2);
    expect(result.items[0]?.reasons.map((r) => r.kind)).toEqual([
      "ambiguous-lifecycle",
      "finding-resolution",
    ]);
  });

  it("keys orphans by destination, never by an invented effect id", () => {
    const result = deriveAttention({
      effects: [],
      findings: [
        finding("fnd_4", "OPEN", { adapter_id: "refdest-c2", destination_ref: "dest_524" }),
      ],
      effectsPartial: false,
      findingsPartial: false,
    });
    expect(result.items[0]?.key).toBe("destination:refdest-c2:dest_524");
    expect(result.items[0]?.target).toEqual({ kind: "finding", findingId: "fnd_4" });
  });

  it("groups in formula order and keeps source order within groups", () => {
    const result = deriveAttention({
      effects: [effect(HEX(2), "AMBIGUOUS"), effect(HEX(1), "AMBIGUOUS")],
      findings: [
        finding("fnd_2", "OPEN", { effect_id: HEX(5) }),
        finding("fnd_1", "OPEN", { effect_id: HEX(6) }),
      ],
      effectsPartial: false,
      findingsPartial: false,
    });
    expect(result.items.map((i) => i.key)).toEqual([
      `effect:${HEX(2)}`,
      `effect:${HEX(1)}`,
      `effect:${HEX(5)}`,
      `effect:${HEX(6)}`,
    ]);
  });

  it("marks the worklist partial when either source is partial", () => {
    for (const [effectsPartial, findingsPartial] of [
      [true, false],
      [false, true],
    ] as const) {
      expect(
        deriveAttention({ effects: [], findings: [], effectsPartial, findingsPartial }).partial,
      ).toBe(true);
    }
  });
});
