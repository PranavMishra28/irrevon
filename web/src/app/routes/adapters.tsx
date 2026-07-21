import { useQuery } from "@tanstack/react-query";
import { createFileRoute } from "@tanstack/react-router";
import { DeclarationCard } from "@/features/adapters/declaration-card";
import { AdapterTopology } from "@/features/adapters/topology";
import { apiGet } from "@/shared/api/client";
import { queryKeys } from "@/shared/api/query-keys";
import type { AdaptersPayload } from "@/shared/api/types";
import { Page } from "@/shared/ui/layout/page";
import { useMediaQuery } from "@/shared/ui/use-media";

export const Route = createFileRoute("/adapters")({ component: AdaptersPage });

/**
 * Adapters (REDESIGN-BRIEF §5.7): the declared topology beside the exact
 * declaration cards. On phones the declaration card comes FIRST so exact
 * source fields precede the explanatory view. No drift, test-pass,
 * availability, or live-health claim exists here.
 */
function AdaptersPage() {
  const adapters = useQuery({
    queryKey: queryKeys.adapters(),
    queryFn: () => apiGet<AdaptersPayload>("/api/v1/adapters"),
  });
  const isMobile = !useMediaQuery("(min-width: 768px)");

  return (
    <Page
      title="Adapters"
      lead="Version-pinned capability declarations, rendered field-for-field from the schema-validated documents the engine actually loads — beside the declared (not observed) topology they describe."
    >
      {adapters.isPending ? (
        <div className="min-h-40" aria-busy="true" />
      ) : adapters.isError ? (
        <p className="font-mono text-xs text-text-secondary">{adapters.error.message}</p>
      ) : adapters.data.data.length === 0 ? (
        <div className="max-w-2xl rounded-(--radius-structural) border border-border bg-layer-panel p-5">
          <p className="text-sm text-text-primary">
            No capability declarations are loaded. Without a declaration nothing can dispatch —
            this is a statement about configuration, not about safety.
          </p>
        </div>
      ) : (
        <div className="grid grid-cols-1 gap-5 min-[1120px]:grid-cols-12">
          {/* Mobile: declaration first; desktop: topology left (7), cards right (5). */}
          <div
            className={
              "min-w-0 " +
              (isMobile ? "order-2" : "min-[1120px]:order-1 min-[1120px]:col-span-7")
            }
          >
            <h2 className="border-b border-border-subtle pb-1.5 font-mono text-2xs font-medium tracking-wide text-text-tertiary uppercase">
              Declared topology
            </h2>
            <div className="mt-3">
              <AdapterTopology declarations={adapters.data.data} vertical={isMobile} />
            </div>
            <p className="mt-3 text-2xs text-text-tertiary">
              as_of <span className="font-mono">{adapters.data.as_of}</span>
            </p>
          </div>
          <div
            className={
              "flex min-w-0 flex-col gap-4 " +
              (isMobile ? "order-1" : "min-[1120px]:order-2 min-[1120px]:col-span-5")
            }
          >
            <h2 className="border-b border-border-subtle pb-1.5 font-mono text-2xs font-medium tracking-wide text-text-tertiary uppercase">
              Declarations — the complete twin
            </h2>
            {adapters.data.data.map((declaration) => (
              <div key={declaration.adapter} id={`declaration-${declaration.adapter}`}>
                <DeclarationCard declaration={declaration} />
              </div>
            ))}
          </div>
        </div>
      )}
    </Page>
  );
}
