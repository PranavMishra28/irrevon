import { createFileRoute } from "@tanstack/react-router";
import {
  CLASSIFICATIONS,
  CLASSIFICATION_ATTACHMENT,
  LIFECYCLE_EDGES,
  LIFECYCLE_STATES,
  RESOLUTION_LEGALITY,
  TERMINAL_LIFECYCLE_STATES,
} from "@/shared/contracts/generated/state-model";
import { FindingBadge } from "@/shared/domain/status/finding-badge";
import { LifecyclePill } from "@/shared/domain/status/lifecycle-pill";
import { Page } from "@/shared/ui/layout/page";

export const Route = createFileRoute("/learn/state")({ component: StatePage });

/**
 * Rendered entirely from the generated state model (RFC-002 §3 via codegen).
 * No cell on this page is hand-authored; regeneration is the only way this
 * content changes.
 */

const RESOLUTION_ACTIONS = [
  "COMPENSATED",
  "REDISPATCHED",
  "ACCEPTED_AS_IS",
  "ESCALATED_HUMAN",
] as const;

const th =
  "border-b border-border px-3 py-2 text-left font-mono text-2xs font-medium tracking-wide text-text-tertiary uppercase";
const td = "border-b border-border-subtle px-3 py-1.5 align-middle";

function LegalityCell({ value }: { value: "LEGAL" | "ILLEGAL" | "AUTO" }) {
  if (value === "ILLEGAL") {
    return <span className="font-mono text-2xs text-text-tertiary uppercase">illegal</span>;
  }
  return (
    <span className="font-mono text-2xs font-semibold text-text-primary uppercase">
      {value === "AUTO" ? "auto" : "legal"}
    </span>
  );
}

function StatePage() {
  return (
    <Page
      title="State model"
      lead="Three orthogonal dimensions — execution lifecycle, reconciliation classification, and resolution — generated from the ratified state tables. Every combination not listed as legal is illegal."
    >
      <div className="flex max-w-5xl flex-col gap-8">
        <section>
          <h2 className="text-lg font-semibold text-text-primary">
            A — lifecycle edges (per execution)
          </h2>
          <p className="mt-1 text-sm text-text-secondary">
            Every (from, to) pair not listed is illegal. Cause and actor are part of edge
            legality. Terminal per execution:{" "}
            {TERMINAL_LIFECYCLE_STATES.map((s) => s).join(", ")} — “try again” after a terminal
            state is a new execution, never a lifecycle edge.
          </p>
          <div className="mt-3 overflow-x-auto rounded-(--radius-structural) border border-border bg-layer-panel">
            <table className="w-full border-collapse text-sm">
              <thead>
                <tr>
                  <th className={th}>From</th>
                  <th className={th}>To</th>
                  <th className={th}>Cause</th>
                  <th className={th}>Actors</th>
                </tr>
              </thead>
              <tbody>
                {LIFECYCLE_EDGES.map((edge) => (
                  <tr key={`${edge.from ?? "genesis"}-${edge.to}-${edge.causes.join()}`}>
                    <td className={td}>
                      {edge.from === null ? (
                        <span className="font-mono text-2xs text-text-tertiary uppercase">
                          — genesis
                        </span>
                      ) : (
                        <LifecyclePill value={edge.from} />
                      )}
                    </td>
                    <td className={td}>
                      <LifecyclePill value={edge.to} />
                    </td>
                    <td className={`${td} font-mono text-xs text-text-secondary`}>
                      {edge.causes.join(" | ")}
                    </td>
                    <td className={`${td} font-mono text-xs text-text-secondary`}>
                      {edge.actors.join(", ")}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </section>

        <section>
          <h2 className="text-lg font-semibold text-text-primary">
            A × B — classification attachment
          </h2>
          <p className="mt-1 text-sm text-text-secondary">
            Findings cite effects. UNRECONCILED is the absence of findings, not a finding;
            ORPHANED is destination-keyed only and never attaches to a ledger record.
          </p>
          <div className="mt-3 overflow-x-auto rounded-(--radius-structural) border border-border bg-layer-panel">
            <table className="w-full border-collapse text-sm">
              <thead>
                <tr>
                  <th className={th}>frontier \ classification</th>
                  {CLASSIFICATIONS.map((c) => (
                    <th key={c} className={th}>
                      {c}
                    </th>
                  ))}
                </tr>
              </thead>
              <tbody>
                {LIFECYCLE_STATES.map((lifecycle) => (
                  <tr key={lifecycle}>
                    <td className={td}>
                      <LifecyclePill value={lifecycle} />
                    </td>
                    {CLASSIFICATIONS.map((c) => (
                      <td key={c} className={td}>
                        <LegalityCell value={CLASSIFICATION_ATTACHMENT[lifecycle][c]} />
                      </td>
                    ))}
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </section>

        <section>
          <h2 className="text-lg font-semibold text-text-primary">
            B × C — resolution legality (per finding)
          </h2>
          <p className="mt-1 text-sm text-text-secondary">
            Status chain: OPEN → action → CLOSED; ESCALATED_HUMAN may route to any action.
            “auto” = applied by the system actor in the same settle transaction. This table is
            descriptive — the workbench performs no resolution.
          </p>
          <div className="mt-3 overflow-x-auto rounded-(--radius-structural) border border-border bg-layer-panel">
            <table className="w-full border-collapse text-sm">
              <thead>
                <tr>
                  <th className={th}>classification \ action</th>
                  {RESOLUTION_ACTIONS.map((a) => (
                    <th key={a} className={th}>
                      {a}
                    </th>
                  ))}
                </tr>
              </thead>
              <tbody>
                {CLASSIFICATIONS.map((classification) => (
                  <tr key={classification}>
                    <td className={td}>
                      <FindingBadge value={classification} />
                    </td>
                    {RESOLUTION_ACTIONS.map((action) => (
                      <td key={action} className={td}>
                        <LegalityCell value={RESOLUTION_LEGALITY[classification][action]} />
                      </td>
                    ))}
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </section>
      </div>
    </Page>
  );
}
