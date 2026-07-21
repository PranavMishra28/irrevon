import { createFileRoute } from "@tanstack/react-router";
import { ContractPendingState, Page } from "@/shared/ui/layout/page";

export const Route = createFileRoute("/learn/state")({ component: StatePage });

function StatePage() {
  return (
    <Page
      title="State model"
      lead="Three orthogonal dimensions — execution lifecycle, reconciliation classification, and resolution — answered by different subsystems and never conflated into one badge."
    >
      <div className="max-w-3xl">
        <ContractPendingState
          what="This page renders the generated machine-readable state table: legal transitions, attachment rules, required evidence, and actors. Hand-copying the pre-critique state matrix is prohibited — the table appears when the corrected contract lands."
          blockedOn="BI-2 (generated execution/lifecycle/classification/resolution table)"
        />
      </div>
    </Page>
  );
}
