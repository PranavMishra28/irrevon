import type { ReactNode } from "react";
import { Panel, SunkenWell } from "@/shared/ui/primitives/panel";
import type { CountRow } from "./aggregate";

/**
 * Overview modules (REDESIGN-BRIEF A4/§5.2). Every number is a complete-
 * snapshot count or an explicit refusal; module errors are never zero; no
 * trend, delta, percentage, rate, or "all safe" state exists anywhere here.
 */

/** Skeleton shown only after 150ms (no spinner for local reads). */
export function ModuleSkeleton({ title, visible }: { title: string; visible: boolean }) {
  return (
    <Panel title={title}>
      <div aria-busy="true" className="flex min-h-20 flex-col gap-2">
        {visible ? (
          <>
            <div className="h-4 w-3/4 animate-pulse rounded-(--radius-structural) bg-layer-sunken" />
            <div className="h-4 w-1/2 animate-pulse rounded-(--radius-structural) bg-layer-sunken" />
          </>
        ) : null}
      </div>
    </Panel>
  );
}

/** A module read error is a stated failure, never rendered as zero. */
export function ModuleError({ title, message }: { title: string; message: string }) {
  return (
    <Panel title={title}>
      <p className="font-mono text-2xs font-medium tracking-wide text-text-tertiary uppercase">
        Source unavailable
      </p>
      <p className="mt-1.5 font-mono text-xs break-words text-text-primary">{message}</p>
      <p className="mt-1 text-sm text-text-secondary">
        No count is shown for an unreadable source — an error is not zero.
      </p>
    </Panel>
  );
}

export function PartialSnapshotNotice() {
  return (
    <p className="text-sm text-text-secondary">
      Aggregate unavailable from a partial snapshot.
    </p>
  );
}

/**
 * Count list: an HTML list with visible numerals. The bar is a proportional
 * rendering of the same visible number over the complete snapshot total —
 * never the only carrier of the value.
 */
export function CountList({
  rows,
  total,
  emptyText,
}: {
  rows: CountRow[];
  total: number;
  emptyText: string;
}) {
  if (total === 0) {
    return <p className="text-sm text-text-secondary">{emptyText}</p>;
  }
  const max = Math.max(...rows.map((row) => row.count), 1);
  return (
    <ul className="flex flex-col gap-1.5">
      {rows.map((row) => (
        <li
          key={row.value}
          className="grid grid-cols-[minmax(0,1fr)_auto] items-center gap-x-3"
        >
          <span className="machine-id truncate font-mono text-xs text-text-primary">
            {row.value}
          </span>
          <span className="tabular font-mono text-xs text-text-primary">{row.count}</span>
          <span aria-hidden className="col-span-2 mt-0.5 block h-1 w-full bg-layer-sunken">
            <span
              className="block h-full bg-border-strong"
              style={{ width: `${String(Math.round((row.count / max) * 100))}%` }}
            />
          </span>
        </li>
      ))}
    </ul>
  );
}

export function DistributionModule({
  title,
  rows,
  total,
  complete,
  emptyText,
}: {
  title: string;
  rows: CountRow[];
  total: number;
  complete: boolean;
  emptyText: string;
}) {
  return (
    <Panel title={title} meta={complete ? `${total} recorded` : undefined}>
      {complete ? (
        <CountList rows={rows} total={total} emptyText={emptyText} />
      ) : (
        <PartialSnapshotNotice />
      )}
    </Panel>
  );
}

/**
 * Conceptual architecture diagram — permanently labeled, hand-authored
 * HTML/SVG, wholly separate from the causal-graph implementation. The prose
 * definition list beside it is the accessible twin carrying 100% of the
 * facts.
 */
const ARCH_STAGES: readonly { name: string; responsibility: string }[] = [
  {
    name: "Registrar",
    responsibility:
      "derives the stable effect identity and persists intent before anything dispatches",
  },
  {
    name: "Ledger",
    responsibility:
      "the append-only record of transitions, receipts, decisions, probes, findings",
  },
  {
    name: "Gate",
    responsibility: "allows or denies each dispatch with recorded checks and cited evidence",
  },
  {
    name: "Dispatcher",
    responsibility:
      "carries allowed effects across the irreversible boundary and records receipts",
  },
  { name: "Adapter", responsibility: "the declared capability surface for one destination" },
  { name: "Destination", responsibility: "the external system where effects become real" },
];

const ARCH_RETURNS: readonly { name: string; responsibility: string }[] = [
  {
    name: "Reconciler",
    responsibility: "adjudicates doubt by querying the destination and settling records",
  },
  {
    name: "Sweep",
    responsibility: "walks destination records to surface orphans the ledger never intended",
  },
];

export function ConceptualArchitecture() {
  return (
    <Panel
      title="Architecture"
      meta="CONCEPTUAL — NOT FIXTURE DATA"
      bodyClassName="flex min-w-0 flex-col gap-4 p-(--dt-panel-pad) min-[768px]:flex-row"
    >
      <figure aria-hidden className="min-w-0 flex-1">
        <SunkenWell className="overflow-x-auto">
          <div className="flex min-w-max items-center gap-1 py-1">
            {ARCH_STAGES.map((stage, index) => (
              <span key={stage.name} className="flex items-center gap-1">
                {index > 0 ? (
                  <span className="font-mono text-xs text-text-tertiary">→</span>
                ) : null}
                <span
                  className={
                    "rounded-(--radius-structural) border border-border bg-layer-panel " +
                    "px-2 py-1 font-mono text-2xs font-medium tracking-wide " +
                    "text-text-primary uppercase" +
                    (stage.name === "Dispatcher" ? " border-r-2 border-r-border-strong" : "")
                  }
                >
                  {stage.name}
                </span>
              </span>
            ))}
          </div>
          <div className="mt-2 flex min-w-max items-center gap-2 py-1">
            <span className="font-mono text-xs text-text-tertiary">⟲ returns:</span>
            {ARCH_RETURNS.map((stage) => (
              <span
                key={stage.name}
                className={
                  "rounded-(--radius-structural) border border-dashed border-border " +
                  "px-2 py-1 font-mono text-2xs font-medium tracking-wide " +
                  "text-text-secondary uppercase"
                }
              >
                {stage.name}
              </span>
            ))}
            <span className="text-2xs text-text-tertiary">
              query the destination back into the ledger
            </span>
          </div>
        </SunkenWell>
        <figcaption className="mt-1.5 font-mono text-2xs font-medium tracking-wide text-text-tertiary uppercase">
          Conceptual — not fixture data
        </figcaption>
      </figure>
      <dl className="min-w-0 flex-1 columns-1 gap-x-6 text-sm min-[1120px]:columns-2">
        {[...ARCH_STAGES, ...ARCH_RETURNS].map((stage) => (
          <div key={stage.name} className="mb-2 break-inside-avoid">
            <dt className="font-mono text-2xs font-medium tracking-wide text-text-tertiary uppercase">
              {stage.name}
            </dt>
            <dd className="text-sm text-text-secondary">{stage.responsibility}</dd>
          </div>
        ))}
      </dl>
    </Panel>
  );
}

/** Exact ok/warn/fail numerals over a doctor transcript — never telemetry. */
export function DoctorSummaryGrid({
  summary,
}: {
  summary: { ok: number; warn: number; fail: number; other: number };
}) {
  return (
    <>
      <dl className="grid grid-cols-3 gap-2">
        {(["ok", "warn", "fail"] as const).map((status) => (
          <div key={status}>
            <dt className="font-mono text-2xs tracking-wide text-text-tertiary uppercase">
              {status}
            </dt>
            <dd className="tabular font-mono text-lg text-text-primary">{summary[status]}</dd>
          </div>
        ))}
      </dl>
      {summary.other > 0 ? (
        <p className="mt-1.5 font-mono text-2xs text-text-secondary">
          {summary.other} check(s) carry an unrecognized status — listed verbatim.
        </p>
      ) : null}
    </>
  );
}

export function SourceFreshnessBar({ children }: { children: ReactNode }) {
  return (
    <section
      aria-label="Data sources and freshness"
      className={
        "flex flex-wrap items-baseline gap-x-5 gap-y-1.5 rounded-(--radius-structural) " +
        "border border-border bg-layer-workspace px-(--dt-panel-pad) py-2.5"
      }
    >
      {children}
    </section>
  );
}

export function SourceStamp({ name, asOf }: { name: string; asOf: string | undefined }) {
  return (
    <span className="flex items-baseline gap-1.5">
      <span className="font-mono text-2xs tracking-wide text-text-tertiary uppercase">
        {name}
      </span>
      {asOf !== undefined ? (
        <time dateTime={asOf} className="machine-id font-mono text-xs text-text-secondary">
          {asOf.slice(0, 19).replace("T", " ")}Z
        </time>
      ) : (
        <span className="font-mono text-xs text-text-tertiary">unavailable</span>
      )}
    </span>
  );
}
