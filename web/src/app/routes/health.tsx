import { createFileRoute } from "@tanstack/react-router";
import { isMockMode } from "@/app/data-mode";
import { ContractPendingState, Page } from "@/shared/ui/layout/page";

export const Route = createFileRoute("/health")({ component: HealthPage });

function HealthPage() {
  return (
    <Page
      title="Health"
      lead="Connection and preflight facts. This is a trust utility, not a dashboard — it states only what its contract supplies."
    >
      <div className="flex max-w-3xl flex-col gap-4">
        <section className="rounded-(--radius-structural) border border-border bg-surface-1 p-5">
          <h2 className="text-base font-semibold text-text-primary">Connection</h2>
          <dl className="mt-3 grid grid-cols-[max-content_1fr] gap-x-4 gap-y-1.5 text-sm">
            <dt className="text-text-tertiary">Data mode</dt>
            <dd className="font-mono text-xs text-text-primary">
              {isMockMode ? "mock (fixture-backed review build)" : "live"}
            </dd>
            <dt className="text-text-tertiary">Live endpoint</dt>
            <dd className="text-text-primary">
              {isMockMode
                ? "Not applicable — this build never contacts a live server."
                : "No loopback read server is ratified yet; live mode cannot connect."}
            </dd>
          </dl>
        </section>
        <ContractPendingState
          what="The per-check doctor view (database reachability, privileges, sweep freshness, adapter configuration) renders from a single read-only health JSON contract."
          blockedOn="BI-6 (doctor/health JSON contract and exit semantics)"
        />
      </div>
    </Page>
  );
}
