import type { ComponentType } from "react";
import type {
  Classification,
  EffectClass,
  Lifecycle,
  ResolutionStatus,
  TransportOutcome,
} from "@/shared/contracts/generated/state-model";
import type { CapabilityDeclaration } from "@/shared/contracts/generated/capability-declaration";
import {
  AdapterTierC1,
  AdapterTierC2,
  AdapterTierC3,
  Ambiguous,
  ArrowUpRight,
  Ban,
  Boundary,
  Check,
  CheckSquare,
  Circle,
  CircleCheck,
  CircleDashed,
  Clock,
  Compensated,
  Copy,
  Evidence,
  FileX,
  Ledger,
  OrphanAbsence,
  OrphanSheet,
  Probe,
  Recovery,
  RotateCw,
  Undo2,
  Unlink,
  User,
  X,
} from "@/shared/ui/icons";

/**
 * The single source of status visuals. Every map is exhaustive over the
 * GENERATED enums (state-model.ts, derived from RFC-002 §3): adding an enum
 * member upstream fails typecheck here until a visual is designed.
 *
 * Hue grammar (never crossed): green confirmed-good · red confirmed
 * adverse/absent · amber attention/open work · blue in flight · violet
 * pending adjudication · cyan corrective re-action · neutral inert/void.
 *
 * RunValidityMark is deliberately absent: benchmark validity enums are
 * [BACKEND-BLOCKED: BI-7] and do not exist in any ratified contract yet.
 */

export type StatusHue = "green" | "red" | "amber" | "blue" | "violet" | "cyan" | "neutral";
export type Tier = CapabilityDeclaration["tier"];
export type EvidenceQuality = CapabilityDeclaration["evidence_quality"];

/** UNRECONCILED is the absence of findings (RFC-002 §3.2), displayable as a quiet badge. */
export type ClassificationDisplay = Classification | "UNRECONCILED";

export interface VisualSpec {
  hue: StatusHue;
  Glyph: ComponentType<{ size?: number }>;
  /** dashed = epistemic incompleteness (the verdict is not in yet) */
  dashed?: true;
  /** stronger ink for terminal/settled states */
  strong?: true;
}

export function humanize(value: string): string {
  return value.toLowerCase().replaceAll("_", " ");
}

export const LIFECYCLE_SPEC = {
  INTENDED: { hue: "neutral", Glyph: CircleDashed },
  // ledger, not a storage cylinder: persist-before-dispatch is bookkeeping.
  PERSISTED: { hue: "blue", Glyph: Ledger },
  DISPATCHED: { hue: "blue", Glyph: ArrowUpRight },
  SETTLED_COMMITTED: { hue: "green", Glyph: Check, strong: true },
  SETTLED_FAILED: { hue: "red", Glyph: X, strong: true },
  // the dashed slot holding a question — the flagship state's own grammar,
  // no longer sharing a glyph with the chrome help control.
  AMBIGUOUS: { hue: "violet", Glyph: Ambiguous, dashed: true },
  CANCELLED: { hue: "neutral", Glyph: Ban, strong: true },
} as const satisfies Record<Lifecycle, VisualSpec>;

export const CLASSIFICATION_SPEC = {
  // "awaiting read-back" is precisely the probe drawing.
  UNRECONCILED: { hue: "neutral", Glyph: Probe, dashed: true },
  // evidence returned and cited — the confirmation is a read, not a file.
  CONFIRMED_UNIQUE: { hue: "green", Glyph: Evidence },
  DUPLICATE: { hue: "amber", Glyph: Copy },
  // confirmed-absent is the void-slot drawing, not hyperlink vocabulary.
  LOST: { hue: "red", Glyph: OrphanAbsence },
  ORPHANED: { hue: "red", Glyph: OrphanSheet },
  CONTRADICTED: { hue: "red", Glyph: FileX },
} as const satisfies Record<ClassificationDisplay, VisualSpec>;

export const RESOLUTION_SPEC = {
  OPEN: { hue: "amber", Glyph: Circle },
  // counter-entry, never an undo arrow: compensation is not rollback (ADR-007).
  COMPENSATED: { hue: "cyan", Glyph: Compensated },
  // an adjudicated, recorded re-action that lands once — not a refresh loop.
  REDISPATCHED: { hue: "cyan", Glyph: Recovery },
  ACCEPTED_AS_IS: { hue: "neutral", Glyph: CheckSquare },
  ESCALATED_HUMAN: { hue: "violet", Glyph: User },
  CLOSED: { hue: "green", Glyph: CircleCheck, strong: true },
} as const satisfies Record<ResolutionStatus, VisualSpec>;

export const EFFECT_CLASS_SPEC = {
  IDEMPOTENT: { hue: "neutral", Glyph: Check },
  REVERSIBLE: { hue: "neutral", Glyph: Undo2 },
  COMPENSABLE: { hue: "neutral", Glyph: RotateCw },
  // one-way, not locked-against-access: no security promise is made here.
  IRREVERSIBLE: { hue: "neutral", Glyph: Boundary, strong: true },
} as const satisfies Record<EffectClass, VisualSpec>;

export const TRANSPORT_OUTCOME_SPEC = {
  OK: { hue: "green", Glyph: Check },
  FAILED: { hue: "red", Glyph: X },
  TIMEOUT: { hue: "amber", Glyph: Clock },
  LOST: { hue: "red", Glyph: Unlink },
} as const satisfies Record<TransportOutcome, VisualSpec>;

// One glyph family (capability cells filled 3/2/1) makes the tier ordinal —
// previously three unrelated metaphors (key / magnifier / hidden eye).
export const TIER_SPEC = {
  C1: { hue: "green", Glyph: AdapterTierC1, cells: 3, descriptor: "idempotency-keyed" },
  C2: { hue: "blue", Glyph: AdapterTierC2, cells: 2, descriptor: "queryable" },
  C3: { hue: "neutral", Glyph: AdapterTierC3, cells: 1, descriptor: "opaque" },
} as const satisfies Record<Tier, VisualSpec & { cells: number; descriptor: string }>;

/** Ink/tint utility classes per hue — the only sanctioned status-color usage. */
export const HUE_CLASSES: Record<StatusHue, { ink: string; bg: string; border: string }> = {
  green: { ink: "text-status-green", bg: "bg-status-green-bg", border: "border-status-green" },
  red: { ink: "text-status-red", bg: "bg-status-red-bg", border: "border-status-red" },
  amber: { ink: "text-status-amber", bg: "bg-status-amber-bg", border: "border-status-amber" },
  blue: { ink: "text-status-blue", bg: "bg-status-blue-bg", border: "border-status-blue" },
  violet: {
    ink: "text-status-violet",
    bg: "bg-status-violet-bg",
    border: "border-status-violet",
  },
  cyan: { ink: "text-status-cyan", bg: "bg-status-cyan-bg", border: "border-status-cyan" },
  neutral: {
    ink: "text-status-neutral",
    bg: "bg-status-neutral-bg",
    border: "border-status-neutral",
  },
};

const warned = new Set<string>();

/** Boundary guard: log an unknown enum value exactly once per (dimension, value). */
export function warnUnknownOnce(dimension: string, value: string): void {
  const key = `${dimension}:${value}`;
  if (warned.has(key)) return;
  warned.add(key);
  console.warn(`Unknown ${dimension} value rendered as UNKNOWN: ${JSON.stringify(value)}`);
}
