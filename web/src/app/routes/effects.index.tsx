import { createFileRoute } from "@tanstack/react-router";
import { ContractPendingState, Page } from "@/shared/ui/layout/page";

interface EffectsSearch {
  lifecycle?: string;
}

export const Route = createFileRoute("/effects/")({
  validateSearch: (search: Record<string, unknown>): EffectsSearch => {
    const raw: unknown = search.lifecycle;
    return typeof raw === "string" ? { lifecycle: raw } : {};
  },
  component: EffectsPage,
});

function EffectsPage() {
  return (
    <Page
      title="Effects"
      lead="Every registered effect record: identity, lifecycle, reconciliation classification, and resolution — three separate columns, never one status."
    >
      <ContractPendingState
        what="The effects grid renders only from the corrected post-integration EffectRecord / Q1 envelope schemas. Those schemas have not landed on this branch yet."
        blockedOn="BI-2, BI-3, BI-9 (schemas/*.schema.json on rc/v0.1)"
      />
    </Page>
  );
}
