import { createFileRoute } from "@tanstack/react-router";
import { ContractPendingState, Page } from "@/shared/ui/layout/page";

export const Route = createFileRoute("/findings")({ component: FindingsPage });

function FindingsPage() {
  return (
    <Page
      title="Findings"
      lead="Reconciliation verdicts — including destination-keyed orphans that have no ledger record at all, which is why findings are not just a column on effects."
    >
      <div className="max-w-3xl">
        <ContractPendingState
          what="Findings render from the corrected ReconciliationFinding / Q2 envelope schemas, including the compound destination-keyed subject for orphans."
          blockedOn="BI-2, BI-3, BI-8 (finding, evidence envelope, Q2 contract)"
        />
      </div>
    </Page>
  );
}
