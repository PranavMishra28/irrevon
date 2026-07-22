import { useQuery } from "@tanstack/react-query";
import { createFileRoute } from "@tanstack/react-router";
import { DemoStage, type Lane } from "@/features/demo/stage";
import { apiGet } from "@/shared/api/client";
import { queryKeys } from "@/shared/api/query-keys";
import type { DemoArtifact } from "@/shared/api/types";
import { Page } from "@/shared/ui/layout/page";

/**
 * Demo (REDESIGN-BRIEF §5.8): guided replay of the recorded flagship run.
 * `step` and `lane` are typed URL state; playback is discrete, artifact-
 * only, and never autoplays on load. The browser starts nothing.
 */

const LANES: readonly Lane[] = ["irrevon", "baseline", "both"];

interface DemoSearch {
  step?: number;
  lane?: Lane;
}

export const Route = createFileRoute("/demo")({
  validateSearch: (search: Record<string, unknown>): DemoSearch => {
    const out: DemoSearch = {};
    const rawStep = Number(search.step);
    if (Number.isInteger(rawStep) && rawStep >= 0) out.step = rawStep;
    if (typeof search.lane === "string" && (LANES as readonly string[]).includes(search.lane)) {
      if (search.lane !== "both") out.lane = search.lane as Lane;
    }
    return out;
  },
  component: DemoPage,
});

function DemoPage() {
  const rawSearch = Route.useSearch();
  const navigate = Route.useNavigate();
  const artifact = useQuery({
    queryKey: queryKeys.demoArtifact(),
    queryFn: () => apiGet<DemoArtifact>("/api/v1/demo/artifact"),
  });

  // Re-apply the typed contract (parent search passthrough can leak values),
  // and clamp step to the artifact's exact event count once loaded.
  const step =
    typeof rawSearch.step === "number" &&
    Number.isInteger(rawSearch.step) &&
    rawSearch.step >= 0
      ? artifact.data
        ? Math.min(rawSearch.step, artifact.data.events.length - 1)
        : rawSearch.step
      : 0;
  const lane: Lane =
    typeof rawSearch.lane === "string" && LANES.includes(rawSearch.lane)
      ? rawSearch.lane
      : "both";

  const setPart = (next: { step?: number; lane?: Lane }) => {
    void navigate({
      search: (prev: DemoSearch) => {
        const merged = { ...prev, ...next };
        if (merged.step === 0 || merged.step === undefined) delete merged.step;
        if (merged.lane === "both" || merged.lane === undefined) delete merged.lane;
        return merged;
      },
      replace: true,
    });
  };

  return (
    <Page
      title="Demo"
      lead="Guided replay of a recorded flagship run: a response lost, a real SIGKILL, recovery by query, and a re-synthesized retry denied with evidence — beside the strongest conventional baseline under the identical fault schedule."
    >
      {artifact.isPending ? (
        <div className="min-h-64" aria-busy="true" />
      ) : artifact.isError ? (
        <div
          className="max-w-2xl rounded-(--radius-structural) border-2 border-border-strong bg-layer-panel p-5"
          role="alert"
        >
          <p className="font-mono text-2xs font-medium tracking-wide text-text-primary uppercase">
            Demo artifact unavailable
          </p>
          <p className="mt-2 text-sm text-text-primary">{artifact.error.message}</p>
          <p className="mt-1 text-sm text-text-secondary">
            Playback renders only a recorded artifact; nothing is simulated in its place.
          </p>
        </div>
      ) : (
        <div className="max-w-6xl">
          <p className="mb-4 text-xs text-text-tertiary">
            Replaying the artifact of{" "}
            <span className="font-mono">irrevon demo --seed {artifact.data.summary.seed}</span>{" "}
            — a real engine run with a real crash. The browser never starts an effect.
          </p>
          <DemoStage
            artifact={artifact.data}
            step={step}
            lane={lane}
            onStepChange={(next) => {
              setPart({ step: next });
            }}
            onLaneChange={(next) => {
              setPart({ lane: next });
            }}
          />
        </div>
      )}
    </Page>
  );
}
