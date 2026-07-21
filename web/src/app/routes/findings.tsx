import { useQuery } from "@tanstack/react-query";
import { Link, createFileRoute } from "@tanstack/react-router";
import { apiGet } from "@/shared/api/client";
import { queryKeys } from "@/shared/api/query-keys";
import type { FindingsEnvelope } from "@/shared/api/types";
import { FindingBadge } from "@/shared/domain/status/finding-badge";
import { ResolutionTag } from "@/shared/domain/status/resolution-tag";
import { truncateEffectId, truncateTypedId } from "@/shared/lib/ids";
import { Page } from "@/shared/ui/layout/page";

export const Route = createFileRoute("/findings")({ component: FindingsPage });

function FindingsPage() {
  const findings = useQuery({
    queryKey: queryKeys.findings(),
    queryFn: () => apiGet<FindingsEnvelope>("/api/v1/findings"),
  });

  return (
    <Page
      title="Findings"
      lead="Reconciliation verdicts with their resolution state — including destination-keyed orphans, which have no ledger record at all and can never appear as effect rows."
    >
      {findings.isPending ? (
        <div className="min-h-40" aria-busy="true" />
      ) : findings.isError ? (
        <p className="font-mono text-xs text-text-secondary">{findings.error.message}</p>
      ) : (
        <div className="max-w-4xl overflow-x-auto rounded-(--radius-structural) border border-border bg-surface-1">
          <table className="w-full border-collapse text-sm">
            <thead>
              <tr>
                {[
                  "Finding",
                  "Subject",
                  "Classification",
                  "Resolution",
                  "Evidence",
                  "Created",
                ].map((column) => (
                  <th
                    key={column}
                    scope="col"
                    className="border-b border-border px-3 py-2 text-left font-mono text-2xs font-medium tracking-wide text-text-tertiary uppercase"
                  >
                    {column}
                  </th>
                ))}
              </tr>
            </thead>
            <tbody>
              {findings.data.data.map((finding) => (
                <tr
                  key={finding.finding_id}
                  className="h-(--dt-row-h) border-b border-border-subtle last:border-b-0"
                >
                  <td className="px-3 py-1 font-mono text-xs">
                    {truncateTypedId(finding.finding_id)}
                  </td>
                  <td className="px-3 py-1 font-mono text-xs">
                    {"effect_id" in finding.subject ? (
                      <Link
                        to="/effects/$effectId"
                        params={{ effectId: finding.subject.effect_id }}
                        className="text-accent hover:underline"
                      >
                        {truncateEffectId(finding.subject.effect_id)}
                      </Link>
                    ) : (
                      <span className="text-text-secondary">
                        {finding.subject.adapter_id} · {finding.subject.destination_ref}
                        <span className="ml-1.5 text-2xs text-text-tertiary">
                          (destination-keyed — no ledger record)
                        </span>
                      </span>
                    )}
                  </td>
                  <td className="px-3 py-1">
                    {finding.classification === "DUPLICATE" &&
                    finding.excess_effect_count !== undefined ? (
                      <FindingBadge
                        value="DUPLICATE"
                        excessEffectCount={finding.excess_effect_count}
                      />
                    ) : (
                      <FindingBadge value={finding.classification} />
                    )}
                  </td>
                  <td className="px-3 py-1">
                    <ResolutionTag value={String(finding.resolution.status)} />
                  </td>
                  <td className="px-3 py-1 font-mono text-2xs text-text-tertiary">
                    {finding.evidence_digest.slice(0, 18)}… ({finding.evidence.redaction})
                  </td>
                  <td className="px-3 py-1 font-mono text-2xs text-text-tertiary">
                    <time dateTime={finding.created_at}>
                      {finding.created_at.slice(0, 19).replace("T", " ")}Z
                    </time>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}
    </Page>
  );
}
