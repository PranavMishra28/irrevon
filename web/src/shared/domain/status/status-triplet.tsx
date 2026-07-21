import type { Lifecycle, ResolutionStatus } from "@/shared/contracts/generated/state-model";
import { FindingBadge } from "./finding-badge";
import { LifecyclePill } from "./lifecycle-pill";
import { ResolutionTag } from "./resolution-tag";
import type { ClassificationDisplay } from "./taxonomy";

/**
 * A + B + C composition for the detail header only. Three labeled groups in
 * fixed A→B→C order; never compressed into one badge, never one wrapper
 * color. C is omitted (with an accessible explanation) only when no finding
 * exists.
 */
export function StatusTriplet({
  lifecycle,
  classification,
  resolution,
  excessEffectCount,
}: {
  lifecycle: Lifecycle;
  classification: ClassificationDisplay;
  resolution?: ResolutionStatus | undefined;
  excessEffectCount?: number | undefined;
}) {
  return (
    <div className="flex flex-wrap items-center gap-x-4 gap-y-2">
      <span className="flex items-center gap-1.5">
        <span
          aria-hidden
          className="font-mono text-2xs font-medium tracking-wide text-text-tertiary uppercase"
        >
          A
        </span>
        <LifecyclePill value={lifecycle} />
      </span>
      <span className="flex items-center gap-1.5">
        <span
          aria-hidden
          className="font-mono text-2xs font-medium tracking-wide text-text-tertiary uppercase"
        >
          B
        </span>
        <FindingBadge
          value={classification}
          {...(excessEffectCount !== undefined ? { excessEffectCount } : {})}
        />
      </span>
      {resolution !== undefined ? (
        <span className="flex items-center gap-1.5">
          <span
            aria-hidden
            className="font-mono text-2xs font-medium tracking-wide text-text-tertiary uppercase"
          >
            C
          </span>
          <ResolutionTag value={resolution} />
        </span>
      ) : (
        <span className="sr-only">Resolution: not applicable — no finding exists</span>
      )}
    </div>
  );
}
