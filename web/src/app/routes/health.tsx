import { useQuery } from "@tanstack/react-query";
import { createFileRoute } from "@tanstack/react-router";
import { isMockMode } from "@/app/data-mode";
import { summarizeDoctor } from "@/features/overview/aggregate";
import { DoctorSummaryGrid } from "@/features/overview/modules";
import { apiGet } from "@/shared/api/client";
import { queryKeys } from "@/shared/api/query-keys";
import type { DoctorPayload } from "@/shared/api/types";
import { SUPPORTED_SCHEMA_VERSION } from "@/shared/api/types";
import { DoctorCheckStatus } from "@/shared/domain/status/verdicts";
import { Page } from "@/shared/ui/layout/page";
import { Panel } from "@/shared/ui/primitives/panel";

export const Route = createFileRoute("/health")({ component: HealthPage });

/**
 * Health (REDESIGN-BRIEF §5.9): the doctor contract, verbatim. A trust
 * utility, never a dashboard — no uptime, latency, rate, or run-doctor
 * button. Summary counts equal the checks; mock mode names the transcript
 * as recorded, not live.
 */
function HealthPage() {
  const doctor = useQuery({
    queryKey: queryKeys.health(),
    queryFn: () => apiGet<DoctorPayload>("/api/v1/health"),
  });

  const summary = doctor.data ? summarizeDoctor(doctor.data.checks) : null;
  const hasFail = (summary?.fail ?? 0) > 0;

  return (
    <Page
      title="Health"
      lead="The doctor contract, rendered verbatim: read-only environment validation. It states only what its checks report."
    >
      <div className="grid grid-cols-1 gap-4 min-[768px]:grid-cols-12">
        <div className="flex min-w-0 flex-col gap-4 min-[768px]:col-span-5 min-[1120px]:col-span-4">
          <Panel title="Connection & provenance">
            <dl className="grid grid-cols-[max-content_1fr] gap-x-4 gap-y-1.5 text-sm">
              <dt className="font-mono text-2xs tracking-wide text-text-tertiary uppercase">
                Data mode
              </dt>
              <dd className="font-mono text-xs text-text-primary">
                {isMockMode ? "mock" : "live"}
              </dd>
              <dt className="font-mono text-2xs tracking-wide text-text-tertiary uppercase">
                Transcript
              </dt>
              <dd className="text-xs text-text-secondary">
                {isMockMode
                  ? "a recorded doctor transcript captured from the real engine — not a live probe"
                  : "read from the live connection"}
              </dd>
              <dt className="font-mono text-2xs tracking-wide text-text-tertiary uppercase">
                Schema
              </dt>
              <dd className="font-mono text-xs text-text-primary">
                supported {SUPPORTED_SCHEMA_VERSION}
                {doctor.data ? ` · observed ${doctor.data.schema_version}` : ""}
              </dd>
            </dl>
          </Panel>
          {summary ? (
            <Panel title="Summary" meta={`${doctor.data?.checks.length ?? 0} checks`}>
              <DoctorSummaryGrid summary={summary} />
              {hasFail ? (
                <p
                  role="alert"
                  className="mt-2 border-t border-border-subtle pt-2 text-sm text-text-primary"
                >
                  One or more checks report fail — read the exact messages beside each check.
                </p>
              ) : null}
            </Panel>
          ) : null}
        </div>

        <div className="min-w-0 min-[768px]:col-span-7 min-[1120px]:col-span-8">
          {doctor.isPending ? (
            <div className="min-h-40" aria-busy="true" />
          ) : doctor.isError ? (
            <section
              role="alert"
              className="rounded-(--radius-structural) border-2 border-border-strong bg-layer-panel p-5"
            >
              <p className="font-mono text-2xs font-medium tracking-wide text-text-primary uppercase">
                Doctor unavailable
              </p>
              <p className="mt-2 font-mono text-xs text-text-primary">{doctor.error.message}</p>
            </section>
          ) : (
            <section className="rounded-(--radius-structural) border border-border-subtle bg-layer-panel shadow-(--sys-edge-light)">
              <h2 className="border-b border-border-subtle px-5 py-3 text-base font-semibold text-text-primary">
                Doctor checks
              </h2>
              <ul className="divide-y divide-border-subtle">
                {doctor.data.checks.map((check) => (
                  <li key={check.name} className="flex items-start gap-4 px-5 py-2.5">
                    <span className="w-16 shrink-0 pt-0.5">
                      <DoctorCheckStatus value={check.status} />
                    </span>
                    <div className="min-w-0">
                      <p className="font-mono text-xs font-medium text-text-primary">
                        {check.name}
                      </p>
                      <p className="text-sm text-text-secondary">{check.message}</p>
                      {check.hint !== null && check.hint !== "" ? (
                        <p className="mt-0.5 font-mono text-2xs break-words text-text-tertiary">
                          hint: {check.hint}
                        </p>
                      ) : null}
                    </div>
                  </li>
                ))}
              </ul>
            </section>
          )}
        </div>
      </div>
    </Page>
  );
}
