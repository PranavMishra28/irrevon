import {
  RESOLUTION_STATUSES,
  type ResolutionStatus,
} from "@/shared/contracts/generated/state-model";
import {
  HUE_CLASSES,
  humanize,
  RESOLUTION_SPEC,
  warnUnknownOnce,
  type VisualSpec,
} from "./taxonomy";
import { UnknownStatus } from "./unknown-status";

/**
 * Dimension C — resolution status. Neutral rectangle with a 3px semantic
 * left bar and an action glyph. Rendered only when a finding exists; the
 * caller renders an explicit accessible "not applicable" otherwise.
 */
export function ResolutionTag({ value }: { value: ResolutionStatus | (string & {}) }) {
  if (!(RESOLUTION_STATUSES as readonly string[]).includes(value)) {
    warnUnknownOnce("resolution", value);
    return <UnknownStatus dimension="resolution" value={value} />;
  }
  const spec: VisualSpec = RESOLUTION_SPEC[value as ResolutionStatus];
  const hue = HUE_CLASSES[spec.hue];
  return (
    <span
      className={
        "inline-flex h-5 items-center gap-1 rounded-(--radius-structural) border border-border-subtle " +
        "bg-layer-sunken py-0 pr-1.5 pl-0 text-text-primary"
      }
    >
      <span className="sr-only">Resolution: {humanize(value)}</span>
      <span aria-hidden className="flex h-full items-center gap-1">
        <span
          className={`h-full w-[3px] rounded-l-(--radius-structural) ${HUE_BAR[spec.hue]}`}
        />
        <span className={hue.ink}>
          <spec.Glyph size={12} />
        </span>
        <span className="font-mono text-2xs font-medium tracking-wide uppercase">{value}</span>
      </span>
    </span>
  );
}

/** Not-applicable marker for tables: no finding exists, said out loud. */
export function ResolutionNotApplicable() {
  return (
    <span className="text-text-tertiary">
      <span className="sr-only">Resolution: not applicable — no finding exists</span>
      <span aria-hidden>—</span>
    </span>
  );
}

const HUE_BAR: Record<string, string> = {
  green: "bg-status-green",
  red: "bg-status-red",
  amber: "bg-status-amber",
  blue: "bg-status-blue",
  violet: "bg-status-violet",
  cyan: "bg-status-cyan",
  neutral: "bg-status-neutral",
};
