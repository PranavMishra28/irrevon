import { LIFECYCLE_STATES, type Lifecycle } from "@/shared/contracts/generated/state-model";
import {
  HUE_CLASSES,
  humanize,
  LIFECYCLE_SPEC,
  warnUnknownOnce,
  type VisualSpec,
} from "./taxonomy";
import { UnknownStatus } from "./unknown-status";

/**
 * Dimension A — execution lifecycle. Filled pill: tinted background, status
 * ink, abstract progress glyph, exact enum label in mono. AMBIGUOUS alone is
 * dashed; terminal states carry a stronger (inked) border. The enum value is
 * the entire API: no label/tone/color/icon props exist.
 */
export function LifecyclePill({ value }: { value: Lifecycle | (string & {}) }) {
  if (!(LIFECYCLE_STATES as readonly string[]).includes(value)) {
    warnUnknownOnce("lifecycle", value);
    return <UnknownStatus dimension="lifecycle" value={value} />;
  }
  const spec: VisualSpec = LIFECYCLE_SPEC[value as Lifecycle];
  const hue = HUE_CLASSES[spec.hue];
  return (
    <span
      className={
        `inline-flex h-5 items-center gap-1 rounded-full border px-2 ${hue.bg} ${hue.ink} ` +
        (spec.dashed ? "border-dashed " : "") +
        (spec.strong ? hue.border : "border-transparent")
      }
    >
      <span className="sr-only">Lifecycle: {humanize(value)}</span>
      <span aria-hidden className="flex items-center gap-1">
        <spec.Glyph size={12} />
        <span className="font-mono text-2xs font-medium tracking-wide uppercase">{value}</span>
      </span>
    </span>
  );
}
