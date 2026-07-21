import type { InspectPayload } from "@/shared/api/types";
import { FindingBadge } from "@/shared/domain/status/finding-badge";
import { LifecyclePill } from "@/shared/domain/status/lifecycle-pill";
import { ResolutionTag } from "@/shared/domain/status/resolution-tag";
import { TransportOutcomeInline } from "@/shared/domain/status/supporting-status";

/**
 * Semantic oldest-first <ol> over the merged ledger evidence; the rail
 * visuals are aria-hidden. Dispatch is the single irreversible boundary:
 * dashed rail before, solid after, one ratchet mark. A recovery-actor
 * adjudication renders the crash/restart seam (the recovery replay is the
 * recorded fact; the crash itself leaves no ledger row and none is invented).
 */

interface TimelineEvent {
  key: string;
  at: string;
  title: React.ReactNode;
  detail?: React.ReactNode;
  actor: string;
  anchor?: string;
  /** true from the DISPATCHED transition onward */
  postDispatch: boolean;
  isDispatchBoundary: boolean;
  restartSeamBefore: boolean;
  gapBefore?: string;
}

function formatGap(ms: number): string {
  if (ms >= 3_600_000) return `${(ms / 3_600_000).toFixed(1)} h`;
  if (ms >= 60_000) return `${Math.round(ms / 60_000)} min`;
  return `${Math.round(ms / 1000)} s`;
}

export function buildTimeline(payload: InspectPayload): TimelineEvent[] {
  interface Raw {
    key: string;
    at: string;
    order: number;
    title: React.ReactNode;
    detail?: React.ReactNode;
    actor: string;
    anchor?: string;
    dispatchBoundary?: boolean;
    recoverySeam?: boolean;
  }
  const raw: Raw[] = [];

  for (const t of payload.timeline) {
    raw.push({
      key: `t${t.transition_seq}`,
      at: t.created_at,
      order: 0,
      title: (
        <span className="flex flex-wrap items-center gap-1.5">
          {t.from_state === null ? (
            <span className="font-mono text-xs text-text-tertiary">∅</span>
          ) : (
            <LifecyclePill value={t.from_state} />
          )}
          <span aria-hidden className="text-text-tertiary">
            →
          </span>
          <span className="sr-only">to</span>
          <LifecyclePill value={t.to_state} />
        </span>
      ),
      detail: (
        <span className="font-mono text-2xs text-text-tertiary">
          cause {t.cause} · step {t.step}
        </span>
      ),
      actor: t.actor,
      dispatchBoundary: t.to_state === "DISPATCHED",
      recoverySeam: t.actor === "recovery",
    });
  }
  for (const r of payload.receipts) {
    raw.push({
      key: `r${r.receipt_id}`,
      at: r.recorded_at,
      order: 1,
      title: (
        <span className="flex flex-wrap items-center gap-1.5">
          <span className="text-sm">
            attempt {r.attempt_no} ({r.kind})
          </span>
          <TransportOutcomeInline value={r.transport_outcome} />
        </span>
      ),
      detail: (
        <a
          href={`#receipt-${r.receipt_id}`}
          className="font-mono text-2xs text-accent hover:underline"
        >
          receipt evidence ↓
        </a>
      ),
      actor: r.recorded_by,
    });
  }
  for (const d of payload.gate_decisions) {
    raw.push({
      key: `g${d.decision_id}`,
      at: d.created_at,
      order: -1,
      title: (
        <span className="text-sm">
          gate {d.outcome}
          {d.deny_check !== null ? (
            <span className="font-mono text-xs"> (check={d.deny_check})</span>
          ) : null}
        </span>
      ),
      detail: (
        <a
          href={`#decision-${d.decision_id}`}
          className="font-mono text-2xs text-accent hover:underline"
        >
          decision log ↓
        </a>
      ),
      actor: "gate",
    });
  }
  for (const f of payload.findings) {
    raw.push({
      key: `f${f.finding_id}`,
      at: f.created_at,
      order: 2,
      title: (
        <span className="flex flex-wrap items-center gap-1.5">
          <span className="text-sm">finding</span>
          {f.classification === "DUPLICATE" && f.excess_effect_count !== null ? (
            <FindingBadge value="DUPLICATE" excessEffectCount={f.excess_effect_count} />
          ) : (
            <FindingBadge value={f.classification} />
          )}
        </span>
      ),
      detail: (
        <a
          href={`#finding-${f.finding_id}`}
          className="font-mono text-2xs text-accent hover:underline"
        >
          reconciliation evidence ↓
        </a>
      ),
      actor: f.created_by,
    });
  }
  for (const res of payload.resolutions) {
    raw.push({
      key: `res${res.resolution_seq}`,
      at: res.created_at,
      order: 3,
      title: (
        <span className="flex flex-wrap items-center gap-1.5">
          <span className="text-sm">resolution</span>
          <ResolutionTag value={res.from_status} />
          <span aria-hidden className="text-text-tertiary">
            →
          </span>
          <span className="sr-only">to</span>
          <ResolutionTag value={res.to_status} />
        </span>
      ),
      actor: res.actor,
    });
  }

  raw.sort((a, b) => a.at.localeCompare(b.at) || a.order - b.order);

  // Gap separators: over an hour, or 10× the median inter-event interval.
  const times = raw.map((e) => new Date(e.at).getTime());
  const deltas = times
    .slice(1)
    .map((t, i) => t - (times[i] ?? t))
    .filter((d) => d > 0);
  const median = deltas.length
    ? [...deltas].sort((a, b) => a - b)[Math.floor(deltas.length / 2)]
    : 0;

  let postDispatch = false;
  let seamPending = false;
  return raw.map((event, index) => {
    const isBoundary = event.dispatchBoundary === true && !postDispatch;
    if (isBoundary) postDispatch = true;
    const restartSeam = event.recoverySeam === true && !seamPending;
    if (restartSeam) seamPending = true;
    const delta = index > 0 ? (times[index] ?? 0) - (times[index - 1] ?? 0) : 0;
    const gap =
      index > 0 &&
      (delta > 3_600_000 || (median !== undefined && median > 0 && delta > median * 10))
        ? formatGap(delta)
        : undefined;
    return {
      key: event.key,
      at: event.at,
      title: event.title,
      detail: event.detail,
      actor: event.actor,
      postDispatch: postDispatch && !isBoundary,
      isDispatchBoundary: isBoundary,
      restartSeamBefore: restartSeam,
      ...(gap !== undefined ? { gapBefore: gap } : {}),
    } satisfies TimelineEvent;
  });
}

function RailNode({ solid }: { solid: boolean }) {
  return (
    <svg aria-hidden viewBox="0 0 12 12" className="size-3 shrink-0 text-text-tertiary">
      <circle
        cx="6"
        cy="6"
        r="4"
        fill={solid ? "currentColor" : "none"}
        stroke="currentColor"
        strokeWidth="1.5"
        strokeDasharray={solid ? undefined : "2 2"}
      />
    </svg>
  );
}

/** The single ratchet mark: D1's ball-in-seat geometry at 12px. */
function RatchetMark() {
  return (
    <svg aria-hidden viewBox="0 0 24 24" className="size-3.5 shrink-0 text-text-primary">
      <path fill="currentColor" d="M2.5 12 H6 L12 18 L18 12 H21.5 V20.5 H2.5 Z" />
      <circle fill="currentColor" cx="12" cy="10.93" r="5" />
    </svg>
  );
}

export function EffectTimeline({ payload }: { payload: InspectPayload }) {
  const events = buildTimeline(payload);
  return (
    <ol className="flex flex-col">
      {events.map((event, index) => (
        <li key={event.key} className="relative">
          {event.gapBefore !== undefined ? (
            <p className="py-1 pl-7 font-mono text-2xs text-text-tertiary">
              — {event.gapBefore} elapsed —
            </p>
          ) : null}
          {event.restartSeamBefore ? (
            <div className="my-1.5 flex items-center gap-2" role="note">
              <span aria-hidden className="h-px flex-1 bg-border-strong" />
              <span className="font-mono text-2xs font-medium tracking-wide text-text-secondary uppercase">
                process crash · restart — recovery replay
              </span>
              <span aria-hidden className="h-px flex-1 bg-border-strong" />
            </div>
          ) : null}
          <div className="flex gap-3 pb-4">
            <span aria-hidden className="relative flex w-4 flex-col items-center">
              {event.isDispatchBoundary ? (
                <RatchetMark />
              ) : (
                <RailNode solid={event.postDispatch} />
              )}
              {index < events.length - 1 ? (
                <span
                  className={
                    "mt-0.5 w-0 flex-1 border-l-2 " +
                    (event.postDispatch || event.isDispatchBoundary
                      ? "border-border-strong"
                      : "border-dashed border-border")
                  }
                />
              ) : null}
            </span>
            <div className="min-w-0 pt-px">
              <div className="flex flex-wrap items-baseline gap-x-2">{event.title}</div>
              <p className="mt-0.5 flex flex-wrap items-center gap-x-2 text-2xs text-text-tertiary">
                <time dateTime={event.at} className="font-mono">
                  {event.at.slice(0, 23).replace("T", " ")}Z
                </time>
                <span>· {event.actor}</span>
                {event.detail}
              </p>
              {event.isDispatchBoundary ? (
                <p className="mt-1.5 border-l-2 border-border-strong pl-2 text-xs text-text-secondary">
                  Externalized — cannot be recalled, only reconciled or compensated.
                </p>
              ) : null}
            </div>
          </div>
        </li>
      ))}
    </ol>
  );
}
