import { Link, createFileRoute } from "@tanstack/react-router";
import { isMockMode } from "@/app/data-mode";
import { Page } from "@/shared/ui/layout/page";

export const Route = createFileRoute("/learn/start")({ component: StartPage });

function StartPage() {
  return (
    <Page
      title="Start here"
      lead="Agents retry; destinations don't forgive. Detent persists a stable business identity before dispatch, and queries ambiguous outcomes instead of guessing."
    >
      <div className="flex max-w-3xl flex-col gap-5">
        <section className="rounded-(--radius-structural) border border-border bg-surface-1 p-5">
          <h2 className="text-lg font-semibold text-text-primary">
            The mechanism, in one pass
          </h2>
          <ol className="mt-3 flex list-decimal flex-col gap-2 pl-5 text-sm text-text-primary">
            <li>
              An intent is registered with <span className="font-mono text-xs">stable_ids</span>{" "}
              — business identifiers, never model output.
            </li>
            <li>
              The intent is persisted to an append-only ledger{" "}
              <strong className="font-medium">before</strong> anything is dispatched: a crash
              before this line is provably effect-free.
            </li>
            <li>
              A deterministic gate checks authority and deduplication, then dispatches —
              crossing the one irreversible boundary.
            </li>
            <li>
              A lost response is recorded as AMBIGUOUS — an open question with a procedure, not
              an alarm. The destination's authoritative status is queried before any redispatch.
            </li>
          </ol>
        </section>

        <section className="rounded-(--radius-structural) border border-border bg-surface-1 p-5">
          <h2 className="text-lg font-semibold text-text-primary">Produce a demo artifact</h2>
          <p className="mt-2 text-sm text-text-secondary">
            The walkthrough replays a recorded artifact. The command that produces it runs in
            your terminal — the browser never starts an effect:
          </p>
          <pre className="mt-3 overflow-x-auto rounded-(--radius-control) border border-border-subtle bg-surface-2 px-3 py-2 font-mono text-xs text-text-primary">
            detent demo --keep
          </pre>
          {isMockMode ? (
            <p className="mt-3 text-sm text-text-secondary">
              This build is fixture-backed: the playback you will see is a synthetic,
              schema-valid artifact — not a live or measured run.
            </p>
          ) : null}
        </section>

        <div className="flex gap-3">
          <Link
            to="/demo"
            className={
              "inline-flex h-8 items-center rounded-(--radius-control) border border-accent " +
              "bg-accent px-3 text-sm font-medium text-text-inverse hover:bg-accent-hover"
            }
          >
            Play the demo
          </Link>
          <Link
            to="/learn/identity"
            className={
              "inline-flex h-8 items-center rounded-(--radius-control) border border-border " +
              "bg-surface-1 px-3 text-sm font-medium text-text-primary hover:bg-surface-2"
            }
          >
            Why identity defeats re-synthesis
          </Link>
        </div>
      </div>
    </Page>
  );
}
