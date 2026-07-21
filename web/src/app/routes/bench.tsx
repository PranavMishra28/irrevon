import { createFileRoute } from "@tanstack/react-router";
import { Page } from "@/shared/ui/layout/page";

export const Route = createFileRoute("/bench")({ component: BenchPage });

function BenchPage() {
  return (
    <Page
      title="Benchmark"
      lead="DetentBench results appear here only from real, append-only run artifacts. Baselines are never weakened so the proposed system wins; negative and null results carry equal prominence."
    >
      <div className="max-w-3xl rounded-(--radius-structural) border border-border bg-surface-1 p-5">
        <h2 className="text-base font-semibold text-text-primary">No benchmark runs exist</h2>
        <p className="mt-2 text-sm text-text-secondary">
          A run appears after the benchmark harness executes against real destination sandboxes
          and produces sealed artifacts. Prerequisites, in order:
        </p>
        <ol className="mt-3 flex list-decimal flex-col gap-1.5 pl-5 text-sm text-text-primary">
          <li>Ratified run/cell/validity/metric schemas (statistical repair pending).</li>
          <li>A preregistration-stamped protocol with the holdout split sealed.</li>
          <li>At least one full fault × effect-class matrix run with retained artifacts.</li>
        </ol>
        <p className="mt-3 text-sm text-text-secondary">
          Until then this page shows no numbers at all — synthetic figures presented as results
          would be a lie with good typography.
        </p>
      </div>
    </Page>
  );
}
