import type { ReactNode } from "react";
import { CornerTicks } from "./inspection-frame";

/**
 * Record card: the 768/375 projection of a table row (REDESIGN-BRIEF A6).
 * A named group with a mono identity line, labeled definition-list fields,
 * and a status slot — every fact the table row carries stays visible; no
 * data hides behind horizontal page scroll. Selection uses the Detent Click
 * inspection frame (exactly one per workspace).
 */
export function RecordCard({
  heading,
  headingId,
  meta,
  fields,
  statuses,
  footer,
  inspected = false,
}: {
  /** Mono identity line, e.g. a truncated effect id + type. */
  heading: ReactNode;
  headingId?: string;
  meta?: ReactNode;
  fields?: readonly { label: string; value: ReactNode }[];
  /** Explicitly labeled status rows (A/B/C) — never combined. */
  statuses?: ReactNode;
  footer?: ReactNode;
  inspected?: boolean;
}) {
  return (
    <article
      aria-labelledby={headingId}
      className={
        "relative flex min-w-0 flex-col gap-2 rounded-(--radius-structural) border " +
        "border-border-subtle bg-layer-panel p-(--dt-panel-pad) shadow-(--sys-edge-light) " +
        (inspected ? "dt-inspected" : "")
      }
    >
      {inspected ? <CornerTicks /> : null}
      <header className="flex min-w-0 items-baseline justify-between gap-2">
        <span id={headingId} className="machine-id min-w-0 font-mono text-xs text-text-primary">
          {heading}
        </span>
        {meta ? (
          <span className="shrink-0 font-mono text-2xs text-text-tertiary">{meta}</span>
        ) : null}
      </header>
      {fields && fields.length > 0 ? (
        <dl className="grid grid-cols-[max-content_1fr] gap-x-3 gap-y-1">
          {fields.map((field) => (
            <div key={field.label} className="col-span-2 grid grid-cols-subgrid items-baseline">
              <dt className="font-mono text-2xs tracking-wide text-text-tertiary uppercase">
                {field.label}
              </dt>
              <dd className="machine-id min-w-0 font-mono text-xs break-words text-text-primary">
                {field.value}
              </dd>
            </div>
          ))}
        </dl>
      ) : null}
      {statuses}
      {footer}
    </article>
  );
}
