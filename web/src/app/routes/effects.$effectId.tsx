import { Link, createFileRoute, notFound } from "@tanstack/react-router";
import { isMockMode } from "@/app/data-mode";
import { ContextRail } from "@/features/effects/context-rail";
import {
  AttemptsSection,
  DecisionLogSection,
  IdentitySection,
  RawJsonSection,
  ReconciliationSection,
  ResynthesisSection,
} from "@/features/effects/evidence";
import { useEffectInspect, useEffectItem } from "@/features/effects/queries";
import { EffectTimeline } from "@/features/effects/timeline";
import { NotFoundError, UnsupportedVersionError } from "@/shared/api/errors";
import { StatusTriplet } from "@/shared/domain/status/status-triplet";
import { EffectClassBadge } from "@/shared/domain/status/supporting-status";
import type { Lifecycle } from "@/shared/contracts/generated/state-model";
import type { ClassificationDisplay } from "@/shared/domain/status/taxonomy";
import { truncateEffectId } from "@/shared/lib/ids";
import { Copy } from "@/shared/ui/icons";
import { useAnnouncer } from "@/shared/ui/layout/live-regions";
import { IconButton } from "@/shared/ui/primitives/button";

const EFFECT_ID_RE = /^[0-9a-f]{64}$/;

/**
 * The canonical investigation surface: 4/5/3 timeline/evidence/context at
 * ≥1440px; context drops below at 1024–1439; single column below 1024.
 * Everything rendered here comes from the inspect payload and the Q1 record
 * view — no derived scores, no recommendations, no mutating control.
 */
export const Route = createFileRoute("/effects/$effectId")({
  beforeLoad: ({ params }) => {
    if (!EFFECT_ID_RE.test(params.effectId)) throw notFound();
  },
  component: EffectDetailPage,
});

function Region({ title, children }: { title: string; children: React.ReactNode }) {
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
  const inspect = useEffectInspect(effectId);
  const item = useEffectItem(effectId);

  const copyId = () => {
    void navigator.clipboard.writeText(effectId).then(() => {
      announce("Effect ID copied");
    });
  };

  if (inspect.isError && inspect.error instanceof NotFoundError) {
    return (
      <div className="mx-auto w-full max-w-2xl px-6 py-10">
        <h1
          tabIndex={-1}
          data-route-heading
          className="text-xl font-semibold text-text-primary"
        >
          No exact match
        </h1>
        <p className="mt-2 text-sm text-text-secondary">
          No ledger record is addressed by{" "}
          <span className="font-mono text-xs break-all">{effectId}</span>. The workbench does
          not guess — an unknown id is not treated as a possible orphan.
        </p>
        <Link
          to="/effects"
          className="mt-4 inline-flex h-8 items-center rounded-(--radius-control) border border-border bg-surface-1 px-3 text-sm font-medium text-text-primary hover:bg-surface-2"
        >
          Go to Effects
        </Link>
      </div>
    );
  }

  if (inspect.isError) {
    const unsupported = inspect.error instanceof UnsupportedVersionError;
    return (
      <div className="mx-auto w-full max-w-2xl px-6 py-10">
        <h1
          tabIndex={-1}
          data-route-heading
          className="text-xl font-semibold text-text-primary"
        >
          {unsupported ? "Unsupported payload version" : "Read failed"}
        </h1>
        <p className="mt-2 font-mono text-xs text-text-secondary">{inspect.error.message}</p>
      </div>
    );
  }

  const payload = inspect.data;
  const record = item.data?.record;

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
        {payload ? (
          <div className="mt-3 flex flex-wrap items-center gap-x-5 gap-y-2">
            <span className="font-mono text-xs text-text-secondary">
              {payload.record.effect_type}
            </span>
            <EffectClassBadge value={payload.record.effect_class} />
            <span className="font-mono text-xs text-text-secondary">
              {payload.record.adapter_id}
            </span>
            <StatusTriplet
              lifecycle={payload.record.lifecycle as Lifecycle}
              classification={payload.classification as ClassificationDisplay}
              resolution={latestOpenResolution(payload)}
              excessEffectCount={payload.findings[0]?.excess_effect_count ?? undefined}
            />
            <span className="ml-auto text-2xs text-text-tertiary">
              data mode <span className="font-mono">{isMockMode ? "mock" : "live"}</span>
            </span>
          </div>
        ) : null}
      </header>

      {payload ? (
        <div className="mt-5 grid grid-cols-1 gap-6 min-[1024px]:grid-cols-12">
          <div className="min-[1024px]:col-span-4">
            <Region title="Timeline">
              <EffectTimeline payload={payload} />
            </Region>
          </div>
          <div className="min-[1024px]:col-span-8 min-[1440px]:col-span-5">
            <Region title="Evidence">
              <div className="flex flex-col gap-4">
                <IdentitySection payload={payload} record={record} />
                <AttemptsSection payload={payload} />
                <ReconciliationSection payload={payload} />
                <ResynthesisSection payload={payload} record={record} />
                <DecisionLogSection payload={payload} />
                <RawJsonSection payload={payload} />
              </div>
            </Region>
          </div>
          <div className="min-[1024px]:col-span-12 min-[1440px]:col-span-3">
            <Region title="Context">
              <ContextRail payload={payload} record={record} />
            </Region>
          </div>
        </div>
      ) : (
        <div className="mt-5 min-h-64" aria-busy="true" />
      )}
    </div>
  );
}

function latestOpenResolution(payload: {
  findings: { finding_id: number }[];
  resolutions: { finding_id: number; to_status: string }[];
}) {
  const finding = payload.findings[payload.findings.length - 1];
  if (!finding) return undefined;
  const chain = payload.resolutions.filter((r) => r.finding_id === finding.finding_id);
  const last = chain[chain.length - 1];
  return (last?.to_status ??
    "OPEN") as import("@/shared/contracts/generated/state-model").ResolutionStatus;
}
