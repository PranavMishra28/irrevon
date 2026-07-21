import { describe, expect, it } from "vitest";
import {
  CLASSIFICATIONS,
  CLASSIFICATION_ATTACHMENT,
  EFFECT_CLASSES,
  LIFECYCLE_EDGES,
  LIFECYCLE_STATES,
  RESOLUTION_LEGALITY,
  RESOLUTION_STATUSES,
  TERMINAL_LIFECYCLE_STATES,
  TRANSPORT_OUTCOMES,
} from "@/shared/contracts/generated/state-model";
import {
  CLASSIFICATION_SPEC,
  EFFECT_CLASS_SPEC,
  LIFECYCLE_SPEC,
  RESOLUTION_SPEC,
  TIER_SPEC,
  TRANSPORT_OUTCOME_SPEC,
} from "./taxonomy";

/**
 * Exhaustiveness meta-tests (F1): every generated enum member has an explicit
 * visual spec, and the generated legality maps have no undefined cells. This
 * is how the frontend notices a state-model change semantically.
 */

describe("visual specs are exhaustive over generated enums", () => {
  it("lifecycle", () => {
    expect(Object.keys(LIFECYCLE_SPEC).sort()).toEqual([...LIFECYCLE_STATES].sort());
  });

  it("classification (+ UNRECONCILED display value)", () => {
    expect(Object.keys(CLASSIFICATION_SPEC).sort()).toEqual(
      [...CLASSIFICATIONS, "UNRECONCILED"].sort(),
    );
  });

  it("resolution", () => {
    expect(Object.keys(RESOLUTION_SPEC).sort()).toEqual([...RESOLUTION_STATUSES].sort());
  });

  it("effect class", () => {
    expect(Object.keys(EFFECT_CLASS_SPEC).sort()).toEqual([...EFFECT_CLASSES].sort());
  });

  it("transport outcome", () => {
    expect(Object.keys(TRANSPORT_OUTCOME_SPEC).sort()).toEqual([...TRANSPORT_OUTCOMES].sort());
  });

  it("tier", () => {
    expect(Object.keys(TIER_SPEC).sort()).toEqual(["C1", "C2", "C3"]);
  });
});

describe("generated state tables have no undefined cells", () => {
  it("every A×B cell is explicit", () => {
    for (const lifecycle of LIFECYCLE_STATES) {
      for (const classification of CLASSIFICATIONS) {
        const cell = CLASSIFICATION_ATTACHMENT[lifecycle][classification];
        expect(["LEGAL", "ILLEGAL"]).toContain(cell);
      }
    }
  });

  it("every B×C action cell is explicit", () => {
    const actions = ["COMPENSATED", "REDISPATCHED", "ACCEPTED_AS_IS", "ESCALATED_HUMAN"];
    for (const classification of CLASSIFICATIONS) {
      for (const action of actions) {
        const cell = (RESOLUTION_LEGALITY[classification] as Record<string, string>)[action];
        expect(["LEGAL", "ILLEGAL", "AUTO"]).toContain(cell);
      }
    }
  });

  it("terminal states are lifecycle members and every edge endpoint is known", () => {
    for (const t of TERMINAL_LIFECYCLE_STATES) {
      expect(LIFECYCLE_STATES).toContain(t);
    }
    for (const edge of LIFECYCLE_EDGES) {
      if (edge.from !== null) expect(LIFECYCLE_STATES).toContain(edge.from);
      expect(LIFECYCLE_STATES).toContain(edge.to);
      expect(edge.causes.length).toBeGreaterThan(0);
      expect(edge.actors.length).toBeGreaterThan(0);
    }
  });

  it("ratified invariants hold in the generated tables", () => {
    // ORPHANED never attaches to a lifecycle frontier (destination-keyed only).
    for (const lifecycle of LIFECYCLE_STATES) {
      expect(CLASSIFICATION_ATTACHMENT[lifecycle].ORPHANED).toBe("ILLEGAL");
    }
    // Redispatching a duplicate manufactures more: illegal, always.
    expect(RESOLUTION_LEGALITY.DUPLICATE.REDISPATCHED).toBe("ILLEGAL");
    // CONFIRMED_UNIQUE auto-accepts in the settle transaction.
    expect(RESOLUTION_LEGALITY.CONFIRMED_UNIQUE.ACCEPTED_AS_IS).toBe("AUTO");
  });
});
