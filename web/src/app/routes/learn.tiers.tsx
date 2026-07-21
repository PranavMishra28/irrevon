import { createFileRoute } from "@tanstack/react-router";
import { Page } from "@/shared/ui/layout/page";

export const Route = createFileRoute("/learn/tiers")({ component: TiersPage });

interface Tier {
  id: "C1" | "C2" | "C3";
  name: string;
  capability: string;
  duplicates: string;
  lost: string;
  boundary: string;
}

const TIERS: readonly Tier[] = [
  {
    id: "C1",
    name: "Idempotency-keyed",
    capability: "Destination accepts a caller-supplied key with a defined replay window.",
    duplicates:
      "PREVENTED within the window — natively. Detent adds no advantage here; the benchmark pre-commits to reporting this null.",
    lost: "Detected via receipts plus query.",
    boundary: "None beyond the replay window. This tier is already solved upstream.",
  },
  {
    id: "C2",
    name: "Queryable",
    capability:
      "Stable external references and a list/status query exist, but there is no dependable native idempotency.",
    duplicates:
      "DETECTED via the authoritative status query; redispatch is safe only after confirmed absence.",
    lost: "Detected via sweep; LOST is provable.",
    boundary:
      "The gap Detent exists for: the destination answers questions but does not deduplicate.",
  },
  {
    id: "C3",
    name: "Opaque",
    capability: "No key, no query, no stable identifier.",
    duplicates: "Client-side dedup of identical operations only.",
    lost: "UNDETECTABLE — an impossibility boundary, demonstrated openly, not hidden.",
    boundary:
      "Reconciliation cannot recover information the destination never exposes. Every method fails here, and the benchmark shows it.",
  },
];

const CELLS = 3;

function TierMeterStatic({ tier }: { tier: Tier }) {
  const filled = tier.id === "C1" ? 3 : tier.id === "C2" ? 2 : 1;
  return (
    <span className="flex items-center gap-1" aria-hidden>
      {Array.from({ length: CELLS }, (_, i) => (
        <span
          key={i}
          className={
            "h-2.5 w-4 rounded-[1px] border " +
            (i < filled ? "border-border-strong bg-surface-3" : "border-border bg-surface-1")
          }
        />
      ))}
    </span>
  );
}

function TiersPage() {
  return (
    <Page
      title="Capability tiers"
      lead="What each destination class makes possible — and impossible. Guarantees stop at the destination's own boundary; nothing below claims otherwise."
    >
      <div className="flex max-w-3xl flex-col gap-4">
        {TIERS.map((tier) => (
          <section
            key={tier.id}
            className="rounded-(--radius-structural) border border-border bg-surface-1 p-5"
          >
            <div className="flex items-center gap-3">
              <span className="font-mono text-sm font-semibold text-text-primary">
                {tier.id}
              </span>
              <TierMeterStatic tier={tier} />
              <h2 className="text-base font-semibold text-text-primary">{tier.name}</h2>
            </div>
            <dl className="mt-3 grid grid-cols-[max-content_1fr] gap-x-4 gap-y-1.5 text-sm">
              <dt className="text-text-tertiary">Capability</dt>
              <dd className="text-text-primary">{tier.capability}</dd>
              <dt className="text-text-tertiary">Duplicates</dt>
              <dd className="text-text-primary">{tier.duplicates}</dd>
              <dt className="text-text-tertiary">Lost effects</dt>
              <dd className="text-text-primary">{tier.lost}</dd>
              <dt className="text-text-tertiary">Boundary</dt>
              <dd className="text-text-primary">{tier.boundary}</dd>
            </dl>
          </section>
        ))}
        <p className="text-sm text-text-secondary">
          No live adapter claims appear here: per-adapter declarations, citations, and
          contract-test evidence belong to the Adapters surface once declarations exist.
        </p>
      </div>
    </Page>
  );
}
