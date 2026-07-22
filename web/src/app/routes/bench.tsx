import { createFileRoute } from "@tanstack/react-router";
import { Page } from "@/shared/ui/layout/page";
import { Panel } from "@/shared/ui/primitives/panel";

export const Route = createFileRoute("/bench")({ component: BenchPage });

/**
 * Bench readiness (REDESIGN-BRIEF §5.10): a deliberate evidence null, not a
 * KPI dashboard. No synthetic metric, result, comparison, or progress
 * percentage; prerequisite truth maps to the canonical repository documents.
 */
function BenchPage() {
  return (
    <Page
      title="Benchmark"
      lead="IrrevonBench results appear here only from real, append-only run artifacts. Baselines are never weakened so the proposed system wins; negative and null results carry equal prominence."
    >
      <div className="grid grid-cols-1 gap-4 min-[1024px]:grid-cols-12">
        <div className="min-w-0 min-[1024px]:col-span-7">
          <Panel title="No benchmark results exist">
            <p className="max-w-[65ch] text-sm text-text-primary">
              The harness, contracts, and integrity gates exist; no confirmatory run does, and
              none can before the human preregistration freeze. This page carries no numbers at
              all — synthetic figures presented as results would be a lie with good typography.
            </p>
            <p className="mt-2 max-w-[65ch] text-sm text-text-secondary">
              Results appear only after the frozen plan executes against real destination
              sandboxes and produces sealed, append-only artifacts. Local mechanism runs are
              labeled non-confirmatory at the schema level and never shown here as results.
            </p>
            <p className="mt-3 border-t border-border-subtle pt-2 text-sm text-text-secondary">
              The negative/null-result commitment is binding: if the runs falsify the design,
              this page reports that with the same prominence a success would get.
            </p>
          </Panel>
        </div>
        <div className="flex min-w-0 flex-col gap-4 min-[1024px]:col-span-5">
          <Panel title="Prerequisites, in order">
            <ol className="flex list-decimal flex-col gap-1.5 pl-5 text-sm text-text-primary">
              <li>
                Benchmark contracts + harness landed (ADR-0030/0032, proposed; ratification
                pending).
              </li>
              <li>A preregistration-stamped protocol with the holdout split sealed.</li>
              <li>
                At least one full fault × effect-class matrix run with retained artifacts.
              </li>
            </ol>
          </Panel>
          <Panel title="Methodology & falsification sources">
            <ul className="flex flex-col gap-1 text-sm text-text-secondary">
              <li>
                <span className="font-mono text-xs">docs/benchmark-preregistration.md</span> —
                DRAFT methodology, holdout and artifact policy
              </li>
              <li>
                <span className="font-mono text-xs">docs/master-doc.md §8</span> — benchmark
                design, baseline ladder, kill criterion
              </li>
            </ul>
            <p className="mt-2 border-t border-border-subtle pt-2 text-2xs text-text-tertiary">
              These are repository documents; the workbench cites them by path rather than
              fetching anything remote.
            </p>
          </Panel>
        </div>
      </div>
    </Page>
  );
}
