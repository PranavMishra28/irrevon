/**
 * Exact-ID parsing for the palette router. No prefix lookup, no fuzzy search:
 * an input either is exactly one addressable identifier or it routes nowhere.
 */

const EFFECT_ID_RE = /^[0-9a-f]{64}$/;
const OPERATION_ID_RE = /^[0-9a-f]{64}:(0|[1-9][0-9]*)$/;
const ULID_BODY = "[0-9A-HJKMNP-TV-Z]{26}";
const RECEIPT_ID_RE = new RegExp(`^rcpt_${ULID_BODY}$`);
const FINDING_ID_RE = new RegExp(`^fnd_${ULID_BODY}$`);
const RUN_ID_RE = new RegExp(`^run_${ULID_BODY}$`);

export type ParsedId =
  | { kind: "effect"; effectId: string }
  | { kind: "operation"; effectId: string; step: number }
  | { kind: "receipt"; id: string }
  | { kind: "finding"; id: string }
  | { kind: "run"; id: string }
  | { kind: "none" };

export function parseExactId(raw: string): ParsedId {
  const input = raw.trim();
  if (EFFECT_ID_RE.test(input)) return { kind: "effect", effectId: input };
  const op = OPERATION_ID_RE.exec(input);
  if (op) {
    const [effectId = "", step = "0"] = input.split(":");
    return { kind: "operation", effectId, step: Number(step) };
  }
  if (RECEIPT_ID_RE.test(input)) return { kind: "receipt", id: input };
  if (FINDING_ID_RE.test(input)) return { kind: "finding", id: input };
  if (RUN_ID_RE.test(input)) return { kind: "run", id: input };
  return { kind: "none" };
}

/** Leading-prefix truncation: 12 hex chars for effect ids; full `:step` stays visible. */
export function truncateEffectId(effectId: string): string {
  return `${effectId.slice(0, 12)}\u2026`;
}

export function truncateOperationId(operationId: string): string {
  const colon = operationId.indexOf(":");
  if (colon === -1) return truncateEffectId(operationId);
  return `${operationId.slice(0, 12)}\u2026${operationId.slice(colon)}`;
}

/** Typed prefix + 6 ULID characters for receipt/finding/run ids. */
export function truncateTypedId(id: string): string {
  const underscore = id.indexOf("_");
  if (underscore === -1) return id;
  return `${id.slice(0, underscore + 7)}\u2026`;
}
