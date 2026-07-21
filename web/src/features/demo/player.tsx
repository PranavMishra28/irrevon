import { Link } from "@tanstack/react-router";
import { useEffect, useRef, useState } from "react";
import type { DemoArtifact, DemoEvent } from "@/shared/api/types";
import { ContrastFailedNotice } from "@/shared/domain/status/verdicts";
import { truncateEffectId } from "@/shared/lib/ids";
import { useAnnouncer } from "@/shared/ui/layout/live-regions";
import { Button } from "@/shared/ui/primitives/button";

/**
 * Fixture-driven guided replay of the captured `detent demo --seed 777`
 * artifact. Step count and event names come from the artifact itself; the
 * narration below annotates known event names and renders unknown ones raw.
 * Explicit play/pause/previous/next/restart; no autoplay loop.
 */

const NARRATION: Record<string, { title: string; body: string }> = {
  registered: {
    title: "Intent registered, persisted before dispatch",
    body: "Stable business identifiers — not model output — hash to the effect id. A crash before this durable write is provably effect-free.",
  },
  dispatch_response_lost: {
    title: "Dispatched; the response is lost",
    body: "The destination committed the order, but the response never arrived. Detent records AMBIGUOUS with evidence — it does not guess.",
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
    title: "B5 baseline: same fault, strongest conventional stack",
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

function eventLeg(event: DemoEvent): "detent" | "b5" {
  return event.event.startsWith("b5_") ? "b5" : "detent";
}

export function DemoPlayer({ artifact }: { artifact: DemoArtifact }) {
  const events = artifact.events;
  const [cursor, setCursor] = useState(0);
  const [playing, setPlaying] = useState(false);
  const timer = useRef<ReturnType<typeof setInterval> | undefined>(undefined);
  const { announce } = useAnnouncer();
  const total = events.length;

  useEffect(() => {
    if (!playing) {
      clearInterval(timer.current);
      return;
    }
    timer.current = setInterval(() => {
      setCursor((c) => {
        if (c + 1 >= total) {
          setPlaying(false);
          return c;
        }
        return c + 1;
      });
    }, 2600);
    return () => {
      clearInterval(timer.current);
    };
  }, [playing, total]);

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

  return (
    <div className="flex flex-col gap-4">
      <div className="flex items-center gap-2" role="group" aria-label="Demo playback controls">
        <Button
          onClick={() => {
            setPlaying((p) => !p);
          }}
          disabled={done && !playing}
        >
          {playing ? "Pause" : "Play"}
        </Button>
        <Button
          onClick={() => {
            setPlaying(false);
            setCursor((c) => Math.max(0, c - 1));
          }}
          disabled={cursor === 0}
        >
          ← Previous
        </Button>
        <Button
          onClick={() => {
            setPlaying(false);
            setCursor((c) => Math.min(total - 1, c + 1));
          }}
          disabled={done}
        >
          Next →
        </Button>
        <Button
          variant="ghost"
          onClick={() => {
            setPlaying(false);
            setCursor(0);
          }}
        >
          Restart
        </Button>
        <span className="ml-auto font-mono text-xs text-text-tertiary" aria-hidden>
          {cursor + 1} / {total}
        </span>
      </div>

      <ol className="flex flex-col" aria-label="Demo events">
        {events.slice(0, cursor + 1).map((event, index) => {
          const narration = NARRATION[event.event];
          const isCurrent = index === cursor;
          const leg = eventLeg(event);
          return (
            <li
              key={`${event.event}-${index}`}
              aria-current={isCurrent ? "step" : undefined}
              className={
                "border-l-2 py-2 pl-4 " +
                (leg === "b5" ? "border-border-strong " : "border-(--color-accent) ") +
                (isCurrent ? "bg-surface-2" : "")
              }
            >
              <p className="flex flex-wrap items-baseline gap-x-2">
                <span className="font-mono text-2xs tracking-wide text-text-tertiary uppercase">
                  {index + 1} · {leg === "b5" ? "B5 baseline" : "Detent"} · {event.event}
                </span>
              </p>
              <p className="mt-0.5 text-sm font-medium text-text-primary">
                {narration?.title ?? `Event: ${event.event}`}
              </p>
              {narration ? (
                <p className="mt-0.5 max-w-2xl text-sm text-text-secondary">{narration.body}</p>
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

      {done ? <ContrastSummary artifact={artifact} /> : null}

      {done && typeof summary.detent_leg.effect_id === "string" ? (
        <div className="flex flex-wrap items-center gap-3 border-t border-border-subtle pt-4">
          <Link
            to="/effects/$effectId"
            params={{ effectId: summary.detent_leg.effect_id }}
            className="inline-flex h-8 items-center rounded-(--radius-control) border border-accent bg-accent px-3 text-sm font-medium text-text-inverse hover:bg-accent-hover"
          >
            Inspect the retained effect {truncateEffectId(summary.detent_leg.effect_id)}
          </Link>
          <Link to="/learn/identity" className="text-sm text-accent hover:underline">
            Why the retry mapped to the same intent
          </Link>
          <Link to="/learn/tiers" className="text-sm text-accent hover:underline">
            Why this worked on C2 and cannot on C3
          </Link>
          <Link to="/effects" className="ml-auto text-sm text-accent hover:underline">
            Continue to Effects →
          </Link>
        </div>
      ) : null}
    </div>
  );
}

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

function EventFacts({ event }: { event: DemoEvent }) {
  const facts = FACT_KEYS.filter((k) => event[k] !== undefined && event[k] !== null);
  if (facts.length === 0) return null;
  return (
    <dl className="mt-1.5 flex flex-wrap gap-x-4 gap-y-0.5">
      {facts.map((key) => (
        <div key={key} className="flex items-baseline gap-1">
          <dt className="font-mono text-2xs text-text-tertiary">{key}</dt>
          <dd className="max-w-72 truncate font-mono text-2xs text-text-primary">
            {String(event[key])}
          </dd>
        </div>
      ))}
    </dl>
  );
}

export function ContrastSummary({ artifact }: { artifact: DemoArtifact }) {
  const { summary } = artifact;
  const holds = summary.contrast_holds;
  return (
    <section
      aria-label="Contrast result"
      className="rounded-(--radius-structural) border-2 border-border-strong bg-surface-1 p-4"
    >
      {!holds ? <ContrastFailedNotice /> : null}
      <h3 className="text-base font-semibold text-text-primary">
        The contrast — identical fault schedule, seed {summary.seed}
      </h3>
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
              Detent (reconcile-by-query)
            </td>
            <td className="border-b border-border-subtle px-3 py-1.5 font-mono tabular">
              {summary.detent_leg.destination_effects ?? "—"}
            </td>
            <td className="border-b border-border-subtle px-3 py-1.5 text-text-secondary">
              {summary.detent_leg.duplicate_rejected === true
                ? "rejected, with cited evidence"
                : "not rejected"}
            </td>
          </tr>
          <tr>
            <td className="px-3 py-1.5">B5 (durable runtime + stable op-ids + keys)</td>
            <td className="px-3 py-1.5 font-mono tabular">
              {summary.b5_leg.destination_effects ?? "—"}
            </td>
            <td className="px-3 py-1.5 text-text-secondary">
              {summary.b5_leg.duplicate_created === true ? "CREATED" : "not created"}
            </td>
          </tr>
        </tbody>
      </table>
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
