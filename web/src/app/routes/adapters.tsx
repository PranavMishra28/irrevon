import { createFileRoute } from "@tanstack/react-router";
import { ContractPendingState, Page } from "@/shared/ui/layout/page";

export const Route = createFileRoute("/adapters")({ component: AdaptersPage });

function AdaptersPage() {
  return (
    <Page
      title="Adapters"
      lead="Each adapter ships a version-pinned capability declaration: tier, idempotency semantics, query surface, and cited evidence — declared, tested, and honest about its limits."
    >
      <div className="flex max-w-3xl flex-col gap-4">
        <section className="rounded-(--radius-structural) border border-border bg-surface-1 p-5">
          <h2 className="text-base font-semibold text-text-primary">
            No live adapter declarations available
          </h2>
          <p className="mt-2 text-sm text-text-secondary">
            This surface lists capability declarations exactly as declared — including negative
            contract-test results like &ldquo;no idempotency&rdquo; recorded as a passing
            expected test. No declarations exist yet, so nothing is listed; no contract-test
            dates are fabricated.
          </p>
        </section>
        <ContractPendingState
          what="Adapter rows require durable adapter-instance and declaration identity from the corrected binding contract."
          blockedOn="BI-1, BI-3 (adapter-instance/destination/declaration binding)"
        />
      </div>
    </Page>
  );
}
