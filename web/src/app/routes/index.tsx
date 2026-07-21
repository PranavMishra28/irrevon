import { Link, createFileRoute } from "@tanstack/react-router";
import { useEffect, useState } from "react";
import { isMockMode } from "@/app/data-mode";
import {
  aggregateEffects,
  aggregateResolutions,
  latestAsOf,
  summarizeDoctor,
} from "@/features/overview/aggregate";
import {
  ConceptualArchitecture,
  DistributionModule,
  DoctorSummaryGrid,
  ModuleError,
  ModuleSkeleton,
  PartialSnapshotNotice,
  SourceFreshnessBar,
  SourceStamp,
} from "@/features/overview/modules";
import {
  useOverviewAdapters,
  useOverviewDoctor,
  useOverviewEffects,
  useOverviewFindings,
} from "@/features/overview/queries";
import { SUPPORTED_SCHEMA_VERSION } from "@/shared/api/types";
import { Panel } from "@/shared/ui/primitives/panel";

/**
 * `/` — the honest overview (REDESIGN-BRIEF A4). Exactly eight modules:
 * effect count distributions, resolution counts, data-mode disclosure,
 * schema versions, source freshness, doctor summary, the conceptual
 * architecture diagram, and the Bench readiness pointer. Counts render only
 * over complete snapshots; module errors are never zero; no trend, delta,
 * percentage, rate, uptime, latency, score, or "all safe" state exists.
 */
export const Route = createFileRoute("/")({ component: OverviewPage });

function useDelayedSkeleton(): boolean {
  const [visible, setVisible] = useState(false);
  useEffect(() => {
    const timer = setTimeout(() => {
      setVisible(true);
    }, 150);
    return () => {
      clearTimeout(timer);
    };
  }, []);
  return visible;
}

function OverviewPage() {
  const effects = useOverviewEffects();
  const findings = useOverviewFindings();
  const adapters = useOverviewAdapters();
  const doctor = useOverviewDoctor();
  const skeletonVisible = useDelayedSkeleton();

  const effectAgg = effects.data ? aggregateEffects(effects.data) : null;
  const resolutionAgg = findings.data ? aggregateResolutions(findings.data) : null;
  const doctorSummary = doctor.data ? summarizeDoctor(doctor.data.checks) : null;

  const asOfs = {
    effects: effects.data?.as_of,
    findings: findings.data?.as_of,
    adapters: adapters.data?.as_of,
  };
  const latest = latestAsOf([asOfs.effects, asOfs.findings, asOfs.adapters]);

  const observedVersions = [
    ...new Set(
      [
        effects.data?.schema_version,
        findings.data?.schema_version,
        adapters.data?.schema_version,
        doctor.data?.schema_version,
      ].filter((v): v is string => typeof v === "string"),
    ),
  ].sort();

  const distribution = (
    title: string,
    kind: "byLifecycle" | "byClassification" | "byAdapter" | "byEffectClass",
  ) => {
    if (effects.isPending) {
      return <ModuleSkeleton title={title} visible={skeletonVisible} />;
    }
    if (effects.isError) return <ModuleError title={title} message={effects.error.message} />;
    if (!effectAgg) return null;
    return (
      <DistributionModule
        title={title}
        rows={effectAgg[kind]}
        total={effectAgg.total}
        complete={effectAgg.complete}
        emptyText="No recorded effects. This does not mean “all safe” — nothing has been registered yet."
      />
    );
  };

  return (
    <div className="mx-auto w-full max-w-[1600px] px-4 py-5 min-[768px]:px-6">
      <header>
        <h1
          tabIndex={-1}
          data-route-heading
          className="text-xl font-semibold text-text-primary"
        >
          Overview
        </h1>
        <p className="mt-1 max-w-3xl text-sm text-text-secondary">
          A snapshot of the recorded ledger, counted only from complete served responses.{" "}
          <Link to="/effects" className="text-accent underline underline-offset-2">
            Effects
          </Link>{" "}
          remains the working surface.
        </p>
      </header>

      <div className="mt-4">
        <SourceFreshnessBar>
          <span className="font-mono text-2xs font-medium tracking-wide text-text-primary uppercase">
            Data mode: {isMockMode ? "mock — synthetic fixture, not live or measured" : "live"}
          </span>
          <SourceStamp name="effects as_of" asOf={asOfs.effects} />
          <SourceStamp name="findings as_of" asOf={asOfs.findings} />
          <SourceStamp name="adapters as_of" asOf={asOfs.adapters} />
          {latest !== null ? (
            <span className="flex items-baseline gap-1.5">
              <span className="font-mono text-2xs tracking-wide text-text-tertiary uppercase">
                latest observed as_of
              </span>
              <time
                dateTime={latest}
                className="machine-id font-mono text-xs text-text-secondary"
              >
                {latest.slice(0, 19).replace("T", " ")}Z
              </time>
              <span className="text-2xs text-text-tertiary">
                (maximum of the source values above)
              </span>
            </span>
          ) : null}
        </SourceFreshnessBar>
      </div>

      <div className="mt-4 grid grid-cols-1 gap-4 min-[768px]:grid-cols-2 min-[1120px]:grid-cols-12">
        <div className="grid grid-cols-1 gap-4 min-[768px]:col-span-1 min-[1120px]:col-span-8 min-[1120px]:grid-cols-2">
          {distribution("Effects by lifecycle", "byLifecycle")}
          {distribution("Effects by classification", "byClassification")}
          {distribution("Effects by adapter", "byAdapter")}
          {distribution("Effects by effect class", "byEffectClass")}
        </div>

        <div className="flex flex-col gap-4 min-[768px]:col-span-1 min-[1120px]:col-span-4">
          {findings.isPending ? (
            <ModuleSkeleton title="Finding resolutions" visible={skeletonVisible} />
          ) : findings.isError ? (
            <ModuleError title="Finding resolutions" message={findings.error.message} />
          ) : resolutionAgg ? (
            <Panel
              title="Finding resolutions"
              meta={resolutionAgg.complete ? `${resolutionAgg.total} findings` : undefined}
            >
              {resolutionAgg.complete ? (
                <>
                  <ul className="flex flex-col gap-1">
                    {resolutionAgg.byStatus.map((row) => (
                      <li key={row.value} className="flex items-baseline justify-between gap-3">
                        <span className="machine-id font-mono text-xs text-text-primary">
                          {row.value}
                        </span>
                        <span className="tabular font-mono text-xs text-text-primary">
                          {row.count}
                        </span>
                      </li>
                    ))}
                  </ul>
                  <p className="mt-2 border-t border-border-subtle pt-2 text-2xs text-text-tertiary">
                    OPEN and ESCALATED_HUMAN are recorded work states, not alerts.
                  </p>
                </>
              ) : (
                <PartialSnapshotNotice />
              )}
            </Panel>
          ) : null}

          {doctor.isPending ? (
            <ModuleSkeleton title="Doctor transcript" visible={skeletonVisible} />
          ) : doctor.isError ? (
            <ModuleError title="Doctor transcript" message={doctor.error.message} />
          ) : doctorSummary ? (
            <Panel title="Doctor transcript" meta={`${doctor.data.checks.length} checks`}>
              <DoctorSummaryGrid summary={doctorSummary} />
              <p className="mt-2 border-t border-border-subtle pt-2 text-2xs text-text-tertiary">
                A recorded transcript of <span className="font-mono">irrevon doctor</span> — not
                live telemetry.{" "}
                <Link to="/health" className="text-accent underline underline-offset-2">
                  Full transcript
                </Link>
              </p>
            </Panel>
          ) : null}

          <Panel title="Schema">
            <dl className="flex flex-col gap-1.5 text-sm">
              <div className="flex items-baseline justify-between gap-3">
                <dt className="font-mono text-2xs tracking-wide text-text-tertiary uppercase">
                  UI-supported version
                </dt>
                <dd className="machine-id font-mono text-xs text-text-primary">
                  {SUPPORTED_SCHEMA_VERSION}
                </dd>
              </div>
              <div className="flex items-baseline justify-between gap-3">
                <dt className="font-mono text-2xs tracking-wide text-text-tertiary uppercase">
                  Observed in loaded payloads
                </dt>
                <dd className="machine-id font-mono text-xs text-text-primary">
                  {observedVersions.length > 0 ? observedVersions.join(", ") : "none loaded"}
                </dd>
              </div>
            </dl>
          </Panel>
        </div>
      </div>

      <div className="mt-4 flex flex-col gap-4">
        <ConceptualArchitecture />
        <Panel title="Bench readiness">
          <p className="max-w-[65ch] text-sm text-text-primary">
            No benchmark run contract or artifact exists. Nothing here is a result.
          </p>
          <p className="mt-1.5 text-sm text-text-secondary">
            <Link to="/bench" className="text-accent underline underline-offset-2">
              Benchmark readiness and prerequisites →
            </Link>
          </p>
        </Panel>
      </div>
    </div>
  );
}
