import { CLASSIFICATIONS } from "@/shared/contracts/generated/state-model";
import {
  CLASSIFICATION_SPEC,
  HUE_CLASSES,
  humanize,
  warnUnknownOnce,
  type ClassificationDisplay,
  type VisualSpec,
} from "./taxonomy";
import { UnknownStatus } from "./unknown-status";

const DISPLAYABLE: readonly string[] = [...CLASSIFICATIONS, "UNRECONCILED"];

/**
 * Dimension B — reconciliation classification. Outlined badge (transparent
 * background, 1px status-ink border, 2px radius) with a pictographic
 * finding-scene glyph. UNRECONCILED (absence of findings) renders dashed.
 * DUPLICATE carries the destination-effect count derived from the schema's
 * excess_effect_count — never a finding count.
 */
export function FindingBadge({
  value,
  excessEffectCount,
}: {
  value: ClassificationDisplay | (string & {});
  /** findings.excess_effect_count from the ratified ledger shape (n − 1). */
  excessEffectCount?: number;
}) {
  if (!DISPLAYABLE.includes(value)) {
    warnUnknownOnce("classification", value);
    return <UnknownStatus dimension="classification" value={value} />;
  }
  const spec: VisualSpec = CLASSIFICATION_SPEC[value as ClassificationDisplay];
  const hue = HUE_CLASSES[spec.hue];
  const destinationEffects =
    value === "DUPLICATE" && excessEffectCount !== undefined
      ? excessEffectCount + 1
      : undefined;
  return (
    <span
      className={
        `inline-flex h-5 items-center gap-1 rounded-(--radius-structural) border bg-transparent px-1.5 ` +
        `${hue.ink} ${hue.border} ${spec.dashed ? "border-dashed" : ""}`
      }
    >
      <span className="sr-only">
        Reconciliation: {humanize(value)}
        {destinationEffects !== undefined ? `, ${destinationEffects} destination effects` : ""}
      </span>
      <span aria-hidden className="flex items-center gap-1">
        <spec.Glyph size={12} />
        <span className="font-mono text-2xs font-medium tracking-wide uppercase">
          {value}
          {destinationEffects !== undefined ? ` ×${destinationEffects}` : ""}
        </span>
      </span>
    </span>
  );
}
