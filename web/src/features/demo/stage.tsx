import { useEffect, useRef, useState } from "react";
import type { ComponentType, KeyboardEvent, ReactNode } from "react";
import type { DemoArtifact, DemoEvent } from "@/shared/api/types";
import { ContrastFailedNotice } from "@/shared/domain/status/verdicts";
import {
  Ambiguous,
  CrashSeam,
  DuplicateReject,
  GateDeny,
  Intent,
  Persist,
  Recovery,
  SeatSettle,
  StableId,
} from "@/shared/ui/icons";
import { getSingleKeyShortcutsEnabled } from "@/shared/lib/prefs";
import { truncateEffectId } from "@/shared/lib/ids";
import { useAnnouncer } from "@/shared/ui/layout/live-regions";
import { Button } from "@/shared/ui/primitives/button";
import { Panel, SunkenWell } from "@/shared/ui/primitives/panel";
import { useMediaQuery } from "@/shared/ui/use-media";

/**
 * Demo stage (REDESIGN-BRIEF §5.8): synchronized Irrevon and baseline lanes
 * over one shared step, an exact per-event scrub rail (one tick per
 * recorded event — the Calibration Rail), a current-event inspector, and
 * the artifact-only contrast table. The graph of events builds only from
 * current and previous event objects; the browser starts nothing.
 */

const NARRATION: Record<string, { title: string; body: string }> = {
  registered: {
    title: "Intent registered, persisted before dispatch",
    body: "Stable business identifiers — not model output — hash to the effect id. A crash before this durable write is provably effect-free.",
  },
  dispatch_response_lost: {
    title: "Dispatched; the response is lost",
    body: "The destination committed the order, but the response never arrived. Irrevon records AMBIGUOUS with evidence — it does not guess.",
  },
  crash: {
    title: "The engine process is killed",
    body: "A real SIGKILL, mid-doubt. The ledger is the only memory that survives.",
  },
  recovered: {
    title: "Restart: recovery replays the ledger",
    body: "Every open doubt is adjudicated by querying the destination BEFORE any new dispatch is accepted.",
  },
  settled_confirmed_unique: {
    title: "Adjudicated: the order exists exactly once",
    body: "The authoritative status query settles the record COMMITTED and attaches a CONFIRMED_UNIQUE finding.",
  },
  resynthesis_collapsed: {
    title: "A re-synthesized retry collapses to the same effect",
    body: "The agent retries with different wording and argument shapes — same order, same stable ids, same effect id. The variant digest is recorded.",
  },
  duplicate_rejected: {
    title: "The gate denies the retry, with evidence",
    body: "Deduplication cites the settled execution, its receipts, its finding, and the recorded parameter variant. A denial is an evidenced outcome, not an error.",
  },
  b5_response_lost: {
    title: "B5 baseline: same fault, developmental file-journal stand-in",
    body: "A durable runtime with stable operation ids AND idempotency keys dispatches; the destination commits; the response is lost on the same cue.",
  },
  b5_restart: {
    title: "B5 restarts from its durable journal",
    body: "The journal survived — exactly as designed.",
  },
  b5_retried: {
    title: "B5 retries with the SAME operation id and key",
    body: "The C2 destination accepts the idempotency key and ignores it — there is no native dedup to honor it.",
  },
  b5_duplicate: {
    title: "Destination read-back: two effects for one intent",
    body: "The duplicate happened, proven by read-back of the destination's own records — not inferred.",
  },
};

// Per-event micro-glyphs (identity brief §1.6): each recorded event name
// maps onto the domain icon set. Unknown events render without a glyph —
// the raw-name fallback stays the honest path.
const EVENT_GLYPH: Record<string, ComponentType<{ size?: number }>> = {
  registered: Persist,
  dispatch_response_lost: Ambiguous,
  crash: CrashSeam,
  recovered: Recovery,
  settled_confirmed_unique: SeatSettle,
  resynthesis_collapsed: StableId,
  duplicate_rejected: GateDeny,
  b5_response_lost: Ambiguous,
  b5_restart: Recovery,
  b5_retried: Intent,
  b5_duplicate: DuplicateReject,
};

const FACT_KEYS = [
  "effect_id",
  "lifecycle",
  "classification",
  "transport_outcome",
  "deny_check",
  "outcome",
  "parameter_variant",
  "destination_effects",
  "exit_status",
  "replayed",
] as const;

export type Lane = "irrevon" | "baseline" | "both";

function eventLeg(event: DemoEvent): "irrevon" | "b5" {
  return event.event.startsWith("b5_") ? "b5" : "irrevon";
}

function EventFacts({ event }: { event: DemoEvent }) {
  const facts = FACT_KEYS.filter((k) => event[k] !== undefined && event[k] !== null);
  if (facts.length === 0) return null;
  return (
    <dl className="mt-1.5 flex flex-wrap gap-x-4 gap-y-0.5">
      {facts.map((key) => (
        <div key={key} className="flex min-w-0 items-baseline gap-1">
          <dt className="font-mono text-2xs text-text-tertiary">{key}</dt>
          <dd className="machine-id min-w-0 max-w-full truncate font-mono text-2xs text-text-primary">
            {String(event[key])}
          </dd>
        </div>
      ))}
    </dl>
  );
}

function LaneList({
  label,
  events,
  cursor,
  accent,
}: {
  label: string;
  events: { event: DemoEvent; index: number }[];
  cursor: number;
  accent: boolean;
}) {
  const shown = events.filter(({ index }) => index <= cursor);
  return (
    <section aria-label={`${label} lane`} className="min-w-0 flex-1">
      <h3 className="border-b border-border-subtle pb-1.5 font-mono text-2xs font-medium tracking-wide text-text-tertiary uppercase">
        {label}
      </h3>
      {shown.length === 0 ? (
        <p className="mt-2 text-2xs text-text-tertiary">No events yet at this step.</p>
      ) : (
        <ol className="mt-1 flex flex-col" aria-label={`${label} events`}>
          {shown.map(({ event, index }) => {
            const narration = NARRATION[event.event];
            const MicroGlyph = EVENT_GLYPH[event.event];
            const isCurrent = index === cursor;
            return (
              <li
                key={`${event.event}-${index}`}
                aria-current={isCurrent ? "step" : undefined}
                className={
                  "border-l-2 py-2 pl-3 transition-colors duration-(--sys-dur-fast) " +
                  (accent ? "border-(--color-accent) " : "border-border-strong ") +
                  (isCurrent ? "bg-(--sys-state-hover)" : "")
                }
              >
                <p className="flex items-center gap-1.5 font-mono text-2xs tracking-wide text-text-tertiary uppercase">
                  {MicroGlyph ? (
                    <span aria-hidden className="text-text-secondary">
                      <MicroGlyph size={16} />
                    </span>
                  ) : null}
                  {index + 1} · {event.event}
                </p>
                <p className="mt-0.5 text-sm font-medium text-text-primary">
                  {narration?.title ?? `Event: ${event.event}`}
                </p>
                {narration ? (
                  <p className="mt-0.5 max-w-2xl text-sm text-text-secondary">
                    {narration.body}
                  </p>
                ) : (
                  <p className="mt-0.5 text-xs text-text-tertiary">
                    Unrecognized event name — shown raw, not narrated.
                  </p>
                )}
                <EventFacts event={event} />
              </li>
            );
          })}
        </ol>
      )}
    </section>
  );
}

export function DemoStage({
  artifact,
  step,
  lane,
  onStepChange,
  onLaneChange,
}: {
  artifact: DemoArtifact;
  step: number;
  lane: Lane;
  onStepChange: (step: number) => void;
  onLaneChange: (lane: Lane) => void;
}) {
  const events = artifact.events;
  const total = events.length;
  const cursor = Math.max(0, Math.min(total - 1, step));
  const [playing, setPlaying] = useState(false);
  const timer = useRef<ReturnType<typeof setInterval> | undefined>(undefined);
  const stageRef = useRef<HTMLDivElement>(null);
  const { announce } = useAnnouncer();
  const isMobile = !useMediaQuery("(min-width: 768px)");

  useEffect(() => {
    if (!playing) {
      clearInterval(timer.current);
      return;
    }
    timer.current = setInterval(() => {
      if (cursor + 1 >= total) {
        setPlaying(false);
      } else {
        onStepChange(cursor + 1);
      }
    }, 2600);
    return () => {
      clearInterval(timer.current);
    };
  }, [playing, cursor, total, onStepChange]);

  useEffect(() => {
    const event = events[cursor];
    if (event) {
      announce(
        `Step ${cursor + 1} of ${total}: ${NARRATION[event.event]?.title ?? event.event}`,
      );
    }
  }, [cursor, events, total, announce]);

  const done = cursor >= total - 1;
  const summary = artifact.summary;
  const current = events[cursor];
  const currentLeg = current ? eventLeg(current) : "irrevon";

  const indexed = events.map((event, index) => ({ event, index }));
  const irrevonEvents = indexed.filter(({ event }) => eventLeg(event) === "irrevon");
  const b5Events = indexed.filter(({ event }) => eventLeg(event) === "b5");

  const goTo = (next: number) => {
    setPlaying(false);
    onStepChange(Math.max(0, Math.min(total - 1, next)));
  };

  const onStageKeyDown = (event: KeyboardEvent<HTMLDivElement>) => {
    if (event.key === "ArrowLeft") {
      event.preventDefault();
      goTo(cursor - 1);
    } else if (event.key === "ArrowRight") {
      event.preventDefault();
      goTo(cursor + 1);
    } else if (event.key === "Home") {
      event.preventDefault();
      goTo(0);
    } else if (event.key === "End") {
      event.preventDefault();
      goTo(total - 1);
    } else if (event.key === " " && getSingleKeyShortcutsEnabled()) {
      const target = event.target;
      if (target instanceof HTMLElement && target.tagName === "BUTTON") return;
      event.preventDefault();
      setPlaying((p) => !p && !done);
    }
  };

  let lanes: ReactNode;
  if (isMobile) {
    lanes = (
      <div>
        <div role="tablist" aria-label="Lanes" className="flex border-b border-border">
          {(["irrevon", "baseline", "both"] as const).map((value) => (
            <button
              key={value}
              type="button"
              role="tab"
              aria-selected={lane === value}
              tabIndex={lane === value ? 0 : -1}
              onClick={() => {
                onLaneChange(value);
              }}
              onKeyDown={(event) => {
                if (event.key === "ArrowRight" || event.key === "ArrowLeft") {
                  event.preventDefault();
                  const order: Lane[] = ["irrevon", "baseline", "both"];
                  const index = order.indexOf(lane);
                  const next =
                    order[
                      (index + (event.key === "ArrowRight" ? 1 : order.length - 1)) %
                        order.length
                    ];
                  if (next) onLaneChange(next);
                }
              }}
              className={
                "min-h-11 border-b-2 px-3 text-sm font-medium capitalize " +
                (lane === value
                  ? "border-(--color-accent) text-text-primary"
                  : "border-transparent text-text-secondary")
              }
            >
              {value}
            </button>
          ))}
        </div>
        <div className="mt-3 flex flex-col gap-4">
          {lane !== "baseline" ? (
            <LaneList label="Irrevon" events={irrevonEvents} cursor={cursor} accent />
          ) : null}
          {lane !== "irrevon" ? (
            <LaneList label="B5 baseline" events={b5Events} cursor={cursor} accent={false} />
          ) : null}
        </div>
      </div>
    );
  } else {
    lanes = (
      <div className="flex flex-col gap-6 min-[1024px]:flex-row">
        <LaneList label="Irrevon" events={irrevonEvents} cursor={cursor} accent />
        <LaneList label="B5 baseline" events={b5Events} cursor={cursor} accent={false} />
      </div>
    );
  }

  return (
    // The stage owns Left/Right/Home/End and (opt-in) Space. Controls below
    // are the visible, redundant path for every shortcut.
    // eslint-disable-next-line jsx-a11y/no-static-element-interactions
    <div ref={stageRef} onKeyDown={onStageKeyDown} className="flex min-w-0 flex-col gap-4">
      <div
        className="flex flex-wrap items-center gap-2"
        role="group"
        aria-label="Demo playback controls"
      >
        <Button
          className="min-h-11 min-[768px]:min-h-(--dt-control-h)"
          onClick={() => {
            setPlaying((p) => !p);
          }}
          disabled={done && !playing}
        >
          {playing ? "Pause" : "Play"}
        </Button>
        <Button
          className="min-h-11 min-[768px]:min-h-(--dt-control-h)"
          onClick={() => {
            goTo(cursor - 1);
          }}
          disabled={cursor === 0}
        >
          ← Previous
        </Button>
        <Button
          className="min-h-11 min-[768px]:min-h-(--dt-control-h)"
          onClick={() => {
            goTo(cursor + 1);
          }}
          disabled={done}
        >
          Next →
        </Button>
        <Button
          variant="ghost"
          className="min-h-11 min-[768px]:min-h-(--dt-control-h)"
          onClick={() => {
            goTo(0);
          }}
        >
          Restart
        </Button>
        <span className="tabular ml-auto font-mono text-xs text-text-tertiary" aria-hidden>
          {cursor + 1} / {total}
        </span>
      </div>

      {/* Calibration scrub rail: one tick per recorded event, no filler. */}
      <div
        role="group"
        aria-label={`Scrub rail — ${total} recorded events`}
        className="flex items-end gap-0.5 border-b border-border-subtle pb-2 min-[480px]:gap-1"
      >
        {events.map((event, index) => (
          <button
            key={`${event.event}-${index}`}
            type="button"
            aria-label={`Go to step ${index + 1}: ${event.event}`}
            aria-current={index === cursor ? "step" : undefined}
            onClick={() => {
              goTo(index);
            }}
            // Width can drop below target size at 320: the 44px Previous/Next
            // buttons are the equivalent stepping control (WCAG 2.5.8 exception).
            className={
              "flex min-h-6 min-w-4 flex-1 items-end justify-center " +
              "hover:bg-(--sys-state-hover) min-[480px]:min-w-6"
            }
          >
            <span
              aria-hidden
              className={
                "w-0.5 " +
                (index === cursor
                  ? "h-4 bg-(--color-accent)"
                  : index < cursor
                    ? "h-2.5 bg-border-strong"
                    : "h-2 bg-border")
              }
            />
          </button>
        ))}
      </div>

      {lanes}

      {current ? (
        <Panel title="Current event" meta={`step ${cursor + 1} of ${total} · ${currentLeg}`}>
          <SunkenWell>
            <p className="machine-id font-mono text-xs text-text-primary">{current.event}</p>
            <EventFacts event={current} />
          </SunkenWell>
        </Panel>
      ) : null}

      {done ? <ContrastSummary artifact={artifact} /> : null}

      {done && typeof summary.irrevon_leg.effect_id === "string" ? (
        <div className="flex flex-wrap items-center gap-3 border-t border-border-subtle pt-4">
          <a
            href={`/effects/${summary.irrevon_leg.effect_id}?selected=node%3Agate%3A2`}
            className="inline-flex min-h-11 items-center rounded-(--radius-control) border border-accent bg-accent px-3 text-sm font-medium text-text-inverse hover:bg-accent-hover min-[768px]:min-h-8"
          >
            Inspect the retained effect {truncateEffectId(summary.irrevon_leg.effect_id)}
          </a>
          <a
            href="/learn/identity"
            className="text-sm text-accent underline underline-offset-2"
          >
            Why the retry mapped to the same intent
          </a>
          <a href="/learn/tiers" className="text-sm text-accent underline underline-offset-2">
            Why this worked on C2 and cannot on C3
          </a>
          <a
            href="/effects"
            className="ml-auto text-sm text-accent underline underline-offset-2"
          >
            Continue to Effects →
          </a>
        </div>
      ) : null}
    </div>
  );
}

export function ContrastSummary({ artifact }: { artifact: DemoArtifact }) {
  const { summary } = artifact;
  const holds = summary.contrast_holds;
  return (
    <section
      aria-label="Contrast result"
      className={
        "rounded-(--radius-structural) border-2 border-border-strong bg-layer-panel p-4 " +
        "shadow-(--sys-edge-light)"
      }
    >
      {!holds ? <ContrastFailedNotice /> : null}
      <h3 className="text-base font-semibold text-text-primary">
        The contrast — identical fault schedule, seed {summary.seed}
      </h3>
      <div
        role="group"
        aria-label="Contrast table, scroll horizontally if needed"
        tabIndex={-1}
        className="overflow-x-auto"
      >
        <table className="mt-3 w-full max-w-xl border-collapse text-sm">
          <thead>
            <tr>
              {["Leg", "Destination effects", "Duplicate?"].map((h) => (
                <th
                  key={h}
                  scope="col"
                  className="border-b border-border px-3 py-1.5 text-left font-mono text-2xs font-medium tracking-wide text-text-tertiary uppercase"
                >
                  {h}
                </th>
              ))}
            </tr>
          </thead>
          <tbody>
            <tr>
              <td className="border-b border-border-subtle px-3 py-1.5">
                Irrevon (reconcile-by-query)
              </td>
              <td className="tabular border-b border-border-subtle px-3 py-1.5 font-mono">
                {summary.irrevon_leg.destination_effects ?? "—"}
              </td>
              <td className="border-b border-border-subtle px-3 py-1.5 text-text-secondary">
                {summary.irrevon_leg.duplicate_rejected === true
                  ? "rejected, with cited evidence"
                  : "not rejected"}
              </td>
            </tr>
            <tr>
              <td className="px-3 py-1.5">B5 (durable runtime + stable op-ids + keys)</td>
              <td className="tabular px-3 py-1.5 font-mono">
                {summary.b5_leg.destination_effects ?? "—"}
              </td>
              <td className="px-3 py-1.5 text-text-secondary">
                {summary.b5_leg.duplicate_created === true ? "CREATED" : "not created"}
              </td>
            </tr>
          </tbody>
        </table>
      </div>
      <p className="mt-3 font-mono text-xs text-text-primary">
        contrast_holds: {String(holds)}
      </p>
      <p className="mt-1 text-2xs text-text-tertiary">
        All numbers above are artifact fields from the recorded run — nothing is computed by
        this page.
      </p>
    </section>
  );
}
