import { createFileRoute } from "@tanstack/react-router";
import { ATTENTION_FORMULA, deriveAttention } from "@/features/attention/derive";
import { AttentionWorklist } from "@/features/attention/worklist";
import { useOverviewEffects, useOverviewFindings } from "@/features/overview/queries";
import { Panel, SunkenWell } from "@/shared/ui/primitives/panel";
import { Page } from "@/shared/ui/layout/page";

/**
 * Attention — an exact, unranked derived worklist (REDESIGN-BRIEF A5).
 * The displayed set is precisely the formula below, shown verbatim in the
 * derivation panel. No severity, rank, threshold, SLA, score, owner,
 * assignment, action, or recommendation exists on this page.
 */
export const Route = createFileRoute("/attention")({ component: AttentionPage });

function DerivationPanel({
  ambiguousCount,
  openFindingCount,
  complete,
}: {
  ambiguousCount: number | null;
  openFindingCount: number | null;
  complete: boolean;
}) {
  return (
    <Panel title="Derivation" meta="exact set formula">
      <SunkenWell scrollX scrollLabel="Attention derivation formula">
        <pre className="font-mono text-xs leading-relaxed text-text-primary">
          {ATTENTION_FORMULA}
        </pre>
      </SunkenWell>
      <dl className="mt-3 flex flex-col gap-1.5">
        <div className="flex items-baseline justify-between gap-3">
          <dt className="text-sm text-text-secondary">Ambiguous effects</dt>
          <dd className="tabular font-mono text-xs text-text-primary">
            {complete && ambiguousCount !== null ? ambiguousCount : "—"}
          </dd>
        </div>
        <div className="flex items-baseline justify-between gap-3">
          <dt className="text-sm text-text-secondary">Findings OPEN / ESCALATED_HUMAN</dt>
          <dd className="tabular font-mono text-xs text-text-primary">
            {complete && openFindingCount !== null ? openFindingCount : "—"}
          </dd>
        </div>
      </dl>
      <p className="mt-3 border-t border-border-subtle pt-2 text-2xs text-text-tertiary">
        Items with the same work-item key merge their reasons. Grouping follows the formula's
        order and does not rank the work. Nothing here is scored, ordered by importance, or
        aged.
      </p>
    </Panel>
  );
}

function AttentionPage() {
  const effects = useOverviewEffects();
  const findings = useOverviewFindings();

  const pending = effects.isPending || findings.isPending;
  const error = effects.error ?? findings.error;

  const result =
    effects.data && findings.data
      ? deriveAttention({
          effects: effects.data.data,
          findings: findings.data.data,
          effectsPartial: effects.data.has_more,
          findingsPartial: findings.data.has_more,
        })
      : null;

  return (
    <Page
      title="Attention"
      lead="A derived worklist, not a stored one: exactly the records whose recorded state calls for adjudication or carries open resolution work. No ranking, no score, no SLA."
    >
      <div className="grid grid-cols-1 gap-4 min-[1120px]:grid-cols-12">
        <div className="min-[1120px]:order-2 min-[1120px]:col-span-4">
          <div className="min-[1120px]:sticky min-[1120px]:top-4">
            <DerivationPanel
              ambiguousCount={result?.ambiguousCount ?? null}
              openFindingCount={result?.openFindingCount ?? null}
              complete={result !== null && !result.partial}
            />
          </div>
        </div>
        <div className="min-[1120px]:order-1 min-[1120px]:col-span-8">
          {pending ? (
            <div className="min-h-40" aria-busy="true" />
          ) : error ? (
            <Panel title="Sources unavailable">
              <p className="font-mono text-xs break-words text-text-primary">{error.message}</p>
              <p className="mt-1 text-sm text-text-secondary">
                The worklist derives from the effects and findings reads; with a source
                unreadable it cannot be computed — an error is not an empty list.
              </p>
            </Panel>
          ) : result ? (
            <>
              {result.partial ? (
                <p
                  className={
                    "mb-3 rounded-(--radius-structural) border border-border " +
                    "bg-layer-workspace px-3 py-2 text-sm text-text-primary"
                  }
                >
                  A source snapshot is partial — this worklist is partial too.
                </p>
              ) : null}
              {result.items.length === 0 ? (
                <Panel title="Worklist">
                  <p className="text-sm text-text-primary">No records meet the derivation.</p>
                </Panel>
              ) : (
                <AttentionWorklist items={result.items} />
              )}
            </>
          ) : null}
        </div>
      </div>
    </Page>
  );
}
