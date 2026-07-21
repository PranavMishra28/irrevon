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
        what="The effects grid renders only from the ratified EffectRecord / Q1 envelope record schemas. ADR-0019 defers those to the M3 admission ADR, so no rows can be typed or fixture-authored yet."
        blockedOn="BI-3, BI-9 (record schemas — M3 admission ADR per ADR-0019 item 4)"
      />
    </Page>
  );
}
