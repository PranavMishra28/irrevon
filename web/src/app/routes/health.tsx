import { useQuery } from "@tanstack/react-query";
import { createFileRoute } from "@tanstack/react-router";
import { isMockMode } from "@/app/data-mode";
import { apiGet } from "@/shared/api/client";
import { queryKeys } from "@/shared/api/query-keys";
import type { DoctorPayload } from "@/shared/api/types";
import { DoctorCheckStatus } from "@/shared/domain/status/verdicts";
import { Page } from "@/shared/ui/layout/page";

export const Route = createFileRoute("/health")({ component: HealthPage });

/**
 * Renders the `detent doctor --json` contract: per-check name/status/message/
 * hint, verbatim. A trust utility, never a dashboard.
 */
function HealthPage() {
  const doctor = useQuery({
    queryKey: queryKeys.health(),
    queryFn: () => apiGet<DoctorPayload>("/api/v1/health"),
  });

  return (
    <Page
      title="Health"
      lead="The doctor contract, rendered verbatim: read-only environment validation. It states only what its checks report."
    >
      <div className="flex max-w-3xl flex-col gap-4">
        <section className="rounded-(--radius-structural) border border-border bg-surface-1 p-5">
          <h2 className="text-base font-semibold text-text-primary">Connection</h2>
          <dl className="mt-3 grid grid-cols-[max-content_1fr] gap-x-4 gap-y-1.5 text-sm">
            <dt className="text-text-tertiary">Data mode</dt>
            <dd className="font-mono text-xs text-text-primary">
              {isMockMode
                ? "mock — this page replays a doctor transcript captured from the real engine"
                : "live"}
            </dd>
          </dl>
        </section>

        {doctor.isPending ? (
          <div className="min-h-40" aria-busy="true" />
        ) : doctor.isError ? (
          <section
            role="alert"
            className="rounded-(--radius-structural) border-2 border-border-strong bg-surface-1 p-5"
          >
            <p className="font-mono text-2xs font-medium tracking-wide text-text-primary uppercase">
              Doctor unavailable
            </p>
            <p className="mt-2 font-mono text-xs text-text-primary">{doctor.error.message}</p>
          </section>
        ) : (
          <section className="rounded-(--radius-structural) border border-border bg-surface-1">
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
                      <p className="mt-0.5 font-mono text-2xs text-text-tertiary">
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
    </Page>
  );
}
