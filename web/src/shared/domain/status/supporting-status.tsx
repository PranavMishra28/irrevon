import {
  EFFECT_CLASSES,
  TRANSPORT_OUTCOMES,
  type EffectClass,
  type TransportOutcome,
} from "@/shared/contracts/generated/state-model";
import {
  EFFECT_CLASS_SPEC,
  HUE_CLASSES,
  humanize,
  TIER_SPEC,
  TRANSPORT_OUTCOME_SPEC,
  warnUnknownOnce,
  type EvidenceQuality,
  type Tier,
  type VisualSpec,
} from "./taxonomy";
import { UnknownStatus } from "./unknown-status";

/**
 * Supporting enums: distinct, smaller idioms so they never masquerade as the
 * three status dimensions.
 */

/** effect_class — neutral outlined square badge; IRREVERSIBLE gets the strong boundary + lock, never a red wash. */
export function EffectClassBadge({ value }: { value: EffectClass | (string & {}) }) {
  if (!(EFFECT_CLASSES as readonly string[]).includes(value)) {
    warnUnknownOnce("effect class", value);
    return <UnknownStatus dimension="effect class" value={value} />;
  }
  const spec: VisualSpec = EFFECT_CLASS_SPEC[value as EffectClass];
  return (
    <span
      className={
        "inline-flex h-5 items-center gap-1 rounded-none border bg-transparent px-1.5 text-text-secondary " +
        (spec.strong ? "border-2 border-border-strong text-text-primary" : "border-border")
      }
    >
      <span className="sr-only">Effect class: {humanize(value)}</span>
      <span aria-hidden className="flex items-center gap-1">
        <spec.Glyph size={12} />
        <span className="font-mono text-2xs font-medium tracking-wide uppercase">{value}</span>
      </span>
    </span>
  );
}

/** transport_outcome — inline icon + exact text, no container (receipt-row context). */
export function TransportOutcomeInline({ value }: { value: TransportOutcome | (string & {}) }) {
  if (!(TRANSPORT_OUTCOMES as readonly string[]).includes(value)) {
    warnUnknownOnce("transport outcome", value);
    return <UnknownStatus dimension="transport outcome" value={value} />;
  }
  const spec: VisualSpec = TRANSPORT_OUTCOME_SPEC[value as TransportOutcome];
  const hue = HUE_CLASSES[spec.hue];
  return (
    <span className={`inline-flex items-center gap-1 ${hue.ink}`}>
      <span className="sr-only">Transport outcome: {humanize(value)}</span>
      <span aria-hidden className="flex items-center gap-1">
        <spec.Glyph size={12} />
        <span className="font-mono text-2xs font-medium tracking-wide uppercase">{value}</span>
      </span>
    </span>
  );
}

const TIERS: readonly string[] = ["C1", "C2", "C3"];

/** tier — three-cell capability meter + glyph + exact tier label. */
export function TierMeter({ value }: { value: Tier | (string & {}) }) {
  if (!TIERS.includes(value)) {
    warnUnknownOnce("capability tier", value);
    return <UnknownStatus dimension="capability tier" value={value} />;
  }
  const spec = TIER_SPEC[value as Tier];
  const hue = HUE_CLASSES[spec.hue];
  return (
    <span className={`inline-flex items-center gap-1.5 ${hue.ink}`}>
      <span className="sr-only">
        Capability tier {value}: {spec.descriptor}
      </span>
      <span aria-hidden className="flex items-center gap-1.5">
        <span className="flex items-center gap-px">
          {[0, 1, 2].map((i) => (
            <span
              key={i}
              className={
                "h-2 w-3 border " +
                (i < spec.cells
                  ? `${hue.border} ${HUE_CLASSES[spec.hue].bg}`
                  : "border-border bg-transparent")
              }
            />
          ))}
        </span>
        <spec.Glyph size={12} />
        <span className="font-mono text-2xs font-medium tracking-wide uppercase">{value}</span>
      </span>
    </span>
  );
}

const QUALITIES: readonly string[] = ["VF", "EI"];

const QUALITY_DEFINITION: Record<EvidenceQuality, string> = {
  VF: "verified fact — explicit statement in destination documentation",
  EI: "evidence-backed inference — e.g. absence from a complete parameter list",
};

/** evidence_quality — mono bracket tag; solid border for VF, dashed for EI (inference). */
export function EvidenceQualityTag({ value }: { value: EvidenceQuality | (string & {}) }) {
  if (!QUALITIES.includes(value)) {
    warnUnknownOnce("evidence quality", value);
    return <UnknownStatus dimension="evidence quality" value={value} />;
  }
  const quality = value as EvidenceQuality;
  return (
    <span
      className={
        "inline-flex h-5 items-center rounded-(--radius-structural) border bg-transparent px-1 " +
        "font-mono text-2xs font-medium text-text-secondary " +
        (quality === "EI" ? "border-dashed border-border-strong" : "border-border-strong")
      }
    >
      <span className="sr-only">
        Evidence quality {quality}: {QUALITY_DEFINITION[quality]}
      </span>
      <span aria-hidden>[{quality}]</span>
    </span>
  );
}
