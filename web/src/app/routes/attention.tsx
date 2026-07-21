import { Link, createFileRoute } from "@tanstack/react-router";
import { Page } from "@/shared/ui/layout/page";

export const Route = createFileRoute("/attention")({ component: AttentionPage });

function AttentionPage() {
  return (
    <Page
      title="Attention"
      lead="Attention is derived, not stored: it is the set of records whose state calls for adjudication or open work. There is no risk ranking, no score, and no SLO here."
    >
      <div className="max-w-3xl rounded-(--radius-structural) border border-border bg-surface-1 p-5">
        <p className="text-sm text-text-primary">
          Ambiguous lifecycle states, open findings, and stale sweeps all surface through the
          Effects grid with exact filters — attention is a filtered view of the same ledger
          facts, never a second source of truth.
        </p>
        <div className="mt-4 flex flex-wrap gap-3">
          <Link
            to="/effects"
            search={{ lifecycle: ["AMBIGUOUS"] }}
            className={
              "inline-flex h-8 items-center rounded-(--radius-control) border border-border " +
              "bg-surface-1 px-3 text-sm font-medium text-text-primary hover:bg-surface-2"
            }
          >
            Ambiguous effects
          </Link>
          <Link
            to="/findings"
            className={
              "inline-flex h-8 items-center rounded-(--radius-control) border border-border " +
              "bg-surface-1 px-3 text-sm font-medium text-text-primary hover:bg-surface-2"
            }
          >
            Findings with open resolutions
          </Link>
        </div>
      </div>
    </Page>
  );
}
