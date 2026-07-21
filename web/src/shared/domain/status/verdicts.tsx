import { Check, CircleDashed, FileX, X } from "@/shared/ui/icons";

/**
 * Non-A/B/C verdict idioms (doctor checks, gate outcomes, integrity).
 * They live here because this is the only module allowed to paint status
 * color, and each keeps glyph + exact text as non-color channels.
 */

const DOCTOR_SPEC = {
  ok: { ink: "text-status-green", Glyph: Check },
  warn: { ink: "text-status-amber", Glyph: CircleDashed },
  fail: { ink: "text-status-red", Glyph: X },
} as const;

export function DoctorCheckStatus({ value }: { value: string }) {
  const known =
    value in DOCTOR_SPEC ? DOCTOR_SPEC[value as keyof typeof DOCTOR_SPEC] : undefined;
  const spec = known ?? { ink: "text-status-neutral", Glyph: CircleDashed };
  return (
    <span className={`inline-flex items-center gap-1 ${spec.ink}`}>
      <spec.Glyph size={14} aria-hidden />
      <span className="font-mono text-2xs font-medium uppercase">{value}</span>
    </span>
  );
}

export function GateOutcomeText({ value }: { value: string }) {
  return (
    <span
      className={
        "font-mono text-2xs font-semibold tracking-wide uppercase " +
        (value === "DENY"
          ? "text-status-red"
          : value === "ALLOW"
            ? "text-status-green"
            : "text-status-neutral")
      }
    >
      {value}
    </span>
  );
}

export function GateCheckChip({ check, status }: { check: string; status: string }) {
  return (
    <span
      className={
        "rounded-(--radius-control) border px-1.5 py-0.5 font-mono text-2xs " +
        (status === "denied"
          ? "border-status-red text-status-red"
          : "border-border text-text-secondary")
      }
    >
      {check}: {status}
    </span>
  );
}

export function IntegrityLine({ matches }: { matches: boolean }) {
  if (matches) {
    return (
      <span className="text-xs text-text-primary">
        stored canonical bytes re-hash to the effect_id — ledger integrity holds
      </span>
    );
  }
  return (
    <span className="inline-flex items-center gap-1 text-xs font-semibold text-status-red">
      <FileX size={12} aria-hidden />
      recomputed hash does NOT match — ledger-integrity incident
    </span>
  );
}

/** Demo contrast falsification: prominent, factual, never softened. */
export function ContrastFailedNotice() {
  return (
    <p
      role="alert"
      className="mb-3 inline-flex items-center gap-1.5 font-mono text-sm font-semibold text-status-red uppercase"
    >
      <FileX size={16} aria-hidden />
      Contrast did not hold — this run falsifies the demo's claim and is reported exactly as
      measured.
    </p>
  );
}
