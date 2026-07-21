import { describe, expect, it } from "vitest";
import { parseExactId, truncateEffectId, truncateOperationId, truncateTypedId } from "./ids";

const HEX64 = "a".repeat(64);
const ULID = "01ARZ3NDEKTSV4RRFFQ69G5FAV";

describe("parseExactId", () => {
  it("routes an exact 64-hex effect id", () => {
    expect(parseExactId(HEX64)).toEqual({ kind: "effect", effectId: HEX64 });
  });

  it("trims surrounding whitespace", () => {
    expect(parseExactId(`  ${HEX64}  `)).toEqual({ kind: "effect", effectId: HEX64 });
  });

  it("parses an operation id with step", () => {
    expect(parseExactId(`${HEX64}:3`)).toEqual({
      kind: "operation",
      effectId: HEX64,
      step: 3,
    });
  });

  it("rejects a step with a leading zero", () => {
    expect(parseExactId(`${HEX64}:03`)).toEqual({ kind: "none" });
  });

  it.each([
    [`rcpt_${ULID}`, "receipt"],
    [`fnd_${ULID}`, "finding"],
    [`run_${ULID}`, "run"],
  ])("parses typed id %s as %s", (input, kind) => {
    expect(parseExactId(input)).toEqual({ kind, id: input });
  });

  it("rejects prefixes, uppercase hex, and partial ids", () => {
    expect(parseExactId(HEX64.slice(0, 63))).toEqual({ kind: "none" });
    expect(parseExactId(HEX64.toUpperCase())).toEqual({ kind: "none" });
    expect(parseExactId(`fnd_${ULID.slice(0, 25)}`)).toEqual({ kind: "none" });
    expect(parseExactId(`fnd_${ULID.toLowerCase()}`)).toEqual({ kind: "none" });
    expect(parseExactId("")).toEqual({ kind: "none" });
    expect(parseExactId("effects")).toEqual({ kind: "none" });
  });

  it("rejects ULIDs containing ambiguous letters I, L, O, U", () => {
    for (const bad of ["I", "L", "O", "U"]) {
      expect(parseExactId(`run_${bad.repeat(26)}`)).toEqual({ kind: "none" });
    }
  });
});

describe("truncation", () => {
  it("leading-prefix truncates effect ids to 12 hex", () => {
    expect(truncateEffectId(HEX64)).toBe(`${"a".repeat(12)}\u2026`);
  });

  it("keeps the full :step visible on operation ids", () => {
    expect(truncateOperationId(`${HEX64}:12`)).toBe(`${"a".repeat(12)}\u2026:12`);
  });

  it("keeps typed prefix + 6 ULID chars", () => {
    expect(truncateTypedId(`fnd_${ULID}`)).toBe(`fnd_${ULID.slice(0, 6)}\u2026`);
  });
});
