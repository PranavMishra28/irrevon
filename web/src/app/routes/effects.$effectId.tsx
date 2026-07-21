import { Link, createFileRoute, notFound } from "@tanstack/react-router";
import { isMockMode } from "@/app/data-mode";
import { truncateEffectId } from "@/shared/lib/ids";
import { ContractPendingState } from "@/shared/ui/layout/page";
import { Copy } from "@/shared/ui/icons";
import { IconButton } from "@/shared/ui/primitives/button";
import { useAnnouncer } from "@/shared/ui/layout/live-regions";

const EFFECT_ID_RE = /^[0-9a-f]{64}$/;

/**
 * Canonical investigation surface: full-page 4/5/3 three-region frame
 * (timeline / evidence / context) at wide widths; context drops below at
 * 1280–1439; single column below 1024. The frame ships now; each region
 * renders its honest contract-pending state until the record/evidence
 * schemas land (BI-2, BI-3, BI-8).
 */
export const Route = createFileRoute("/effects/$effectId")({
  beforeLoad: ({ params }) => {
    // Exact-id routing only: anything that is not a 64-hex effect id is not found.
    if (!EFFECT_ID_RE.test(params.effectId)) throw notFound();
  },
  component: EffectDetailPage,
});

function RegionShell({ title, children }: { title: string; children: React.ReactNode }) {
  return (
    <section className="min-w-0">
      <h2 className="border-b border-border pb-2 font-mono text-2xs font-medium tracking-wide text-text-tertiary uppercase">
        {title}
      </h2>
      <div className="pt-3">{children}</div>
    </section>
  );
}

function EffectDetailPage() {
  const { effectId } = Route.useParams();
  const { announce } = useAnnouncer();

  const copyId = () => {
    void navigator.clipboard.writeText(effectId).then(() => {
      announce("Effect ID copied");
    });
  };

  return (
    <div className="mx-auto w-full max-w-[1600px] px-6 py-5">
      <header className="border-b-2 border-border-strong pb-4">
        <nav aria-label="Breadcrumb" className="text-xs text-text-tertiary">
          <Link to="/effects" className="hover:text-text-primary hover:underline">
            Effects
          </Link>
          <span aria-hidden> / </span>
          <span className="font-mono">{truncateEffectId(effectId)}</span>
        </nav>
        <div className="mt-2 flex flex-wrap items-center gap-2">
          <h1
            tabIndex={-1}
            data-route-heading
            className="font-mono text-lg font-semibold break-all text-text-primary"
          >
            {effectId}
          </h1>
          <IconButton label="Copy effect id" onClick={copyId}>
            <Copy size={14} />
          </IconButton>
        </div>
        <p className="mt-2 text-sm text-text-secondary">
          Effect type, class, adapter instance, tier, and the A·B·C status triplet render here
          from the corrected record view. Data mode:{" "}
          <span className="font-mono text-xs">{isMockMode ? "mock" : "live"}</span>; no{" "}
          <span className="font-mono text-xs">as_of</span> is shown because no record source
          exists yet.
        </p>
      </header>

      <div className="mt-5 grid grid-cols-1 gap-6 min-[1024px]:grid-cols-12">
        <div className="min-[1024px]:col-span-4">
          <RegionShell title="Timeline">
            <ContractPendingState
              what="The lifecycle timeline (transitions, attempts, crash seams, the dispatch ratchet boundary) renders from generated transition history."
              blockedOn="BI-2, BI-3 (record schemas deferred to M3 by ADR-0019)"
            />
          </RegionShell>
        </div>
        <div className="min-[1024px]:col-span-8 min-[1440px]:col-span-5">
          <RegionShell title="Evidence">
            <ContractPendingState
              what="Identity derivation, dispatch attempts, receipts, reconciliation findings, the re-synthesis exhibit, and exact JSON disclosure render from the corrected record and evidence schemas."
              blockedOn="BI-1, BI-2, BI-3, BI-8"
            />
          </RegionShell>
        </div>
        <div className="min-[1024px]:col-span-12 min-[1440px]:col-span-3">
          <RegionShell title="Context">
            <ContractPendingState
              what="Authority freshness, adapter binding and tier, latest finding, and the generated legal-state explanation render from the corrected contracts."
              blockedOn="BI-1, BI-2, BI-3"
            />
          </RegionShell>
        </div>
      </div>
    </div>
  );
}
