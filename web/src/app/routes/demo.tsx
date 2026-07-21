import { createFileRoute } from "@tanstack/react-router";
import { ContractPendingState, Page } from "@/shared/ui/layout/page";

export const Route = createFileRoute("/demo")({ component: DemoPage });

function DemoPage() {
  return (
    <Page
      title="Demo"
      lead="Read-only playback of the flagship recovery story: a response lost, a crash survived, an ambiguous outcome adjudicated by query — replayed from a recorded artifact, never started from the browser."
    >
      <div className="max-w-3xl">
        <ContractPendingState
          what="Playback renders each step from the corrected demo artifact schema (three fault legs plus the B5 contrast). The step count and event names come from the artifact, not from prose."
          blockedOn="BI-2, BI-3, BI-5 (demo JSONL/artifact schema)"
        />
      </div>
    </Page>
  );
}
