import { useQuery } from "@tanstack/react-query";
import { createFileRoute } from "@tanstack/react-router";
import { DeclarationCard } from "@/features/adapters/declaration-card";
import { apiGet } from "@/shared/api/client";
import { queryKeys } from "@/shared/api/query-keys";
import type { AdaptersPayload } from "@/shared/api/types";
import { Page } from "@/shared/ui/layout/page";

export const Route = createFileRoute("/adapters")({ component: AdaptersPage });

function AdaptersPage() {
  const adapters = useQuery({
    queryKey: queryKeys.adapters(),
    queryFn: () => apiGet<AdaptersPayload>("/api/v1/adapters"),
  });

  return (
    <Page
      title="Adapters"
      lead="Version-pinned capability declarations, rendered field-for-field from the schema-validated documents the engine actually loads."
    >
      <div className="flex max-w-3xl flex-col gap-4">
        {adapters.isPending ? (
          <div className="min-h-40" aria-busy="true" />
        ) : adapters.isError ? (
          <p className="font-mono text-xs text-text-secondary">{adapters.error.message}</p>
        ) : (
          adapters.data.data.map((declaration) => (
            <DeclarationCard key={declaration.adapter} declaration={declaration} />
          ))
        )}
      </div>
    </Page>
  );
}
