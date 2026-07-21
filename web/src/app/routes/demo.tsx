import { useQuery } from "@tanstack/react-query";
import { createFileRoute } from "@tanstack/react-router";
import { DemoPlayer } from "@/features/demo/player";
import { apiGet } from "@/shared/api/client";
import { queryKeys } from "@/shared/api/query-keys";
import type { DemoArtifact } from "@/shared/api/types";
import { Page } from "@/shared/ui/layout/page";

export const Route = createFileRoute("/demo")({ component: DemoPage });

function DemoPage() {
  const artifact = useQuery({
    queryKey: queryKeys.demoArtifact(),
    queryFn: () => apiGet<DemoArtifact>("/api/v1/demo/artifact"),
  });

  return (
    <Page
      title="Demo"
      lead="Guided replay of a recorded flagship run: a response lost, a real SIGKILL, recovery by query, and a re-synthesized retry denied with evidence — beside the strongest conventional baseline under the identical fault schedule."
    >
      {artifact.isPending ? (
        <div className="min-h-64" aria-busy="true" />
      ) : artifact.isError ? (
        <div
          className="max-w-2xl rounded-(--radius-structural) border-2 border-border-strong bg-surface-1 p-5"
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
        <div className="max-w-3xl">
          <p className="mb-4 text-xs text-text-tertiary">
            Replaying the artifact of{" "}
            <span className="font-mono">detent demo --seed {artifact.data.summary.seed}</span> —
            a real engine run with a real crash. The browser never starts an effect.
          </p>
          <DemoPlayer artifact={artifact.data} />
        </div>
      )}
    </Page>
  );
}
