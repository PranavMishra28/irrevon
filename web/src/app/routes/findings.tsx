import { useQuery } from "@tanstack/react-query";
import { createFileRoute } from "@tanstack/react-router";
import { useEffect } from "react";
import { FindingsList } from "@/features/findings/findings-list";
import { apiGet } from "@/shared/api/client";
import { UnsupportedVersionError } from "@/shared/api/errors";
import { queryKeys } from "@/shared/api/query-keys";
import type { FindingsEnvelope } from "@/shared/api/types";
import { Page } from "@/shared/ui/layout/page";

/**
 * Findings (REDESIGN-BRIEF §5.5): reconciliation verdicts with resolution
 * state, including destination-keyed orphans, which have no ledger record
 * and can never appear as effect rows. `selected` is typed URL state; a
 * stale id leaves the route usable and states the absence — never coerced.
 */

const FINDING_ID_SHAPE = /^fnd_[0-9A-Za-z]{1,32}$/;

interface FindingsSearch {
  selected?: string;
}

export const Route = createFileRoute("/findings")({
  validateSearch: (search: Record<string, unknown>): FindingsSearch => {
    const out: FindingsSearch = {};
    if (typeof search.selected === "string" && FINDING_ID_SHAPE.test(search.selected)) {
      out.selected = search.selected;
    }
    return out;
  },
  component: FindingsPage,
});

function FindingsPage() {
  const rawSearch = Route.useSearch();
  // Re-apply the shape guard: parent-route search passthrough can leak
  // unvalidated params.
  const search: FindingsSearch = { ...rawSearch };
  if (search.selected !== undefined && !FINDING_ID_SHAPE.test(search.selected)) {
    delete search.selected;
  }
  const navigate = Route.useNavigate();
  const findings = useQuery({
    queryKey: queryKeys.findings(),
    queryFn: () => apiGet<FindingsEnvelope>("/api/v1/findings"),
  });

  const setSelected = (findingId: string | null) => {
    void navigate({
      search: findingId === null ? {} : { selected: findingId },
      replace: true,
    });
  };

  const selectedId = search.selected ?? null;

  // Escape clears the selection from anywhere on the route (unless a
  // dialog above owns the key), restoring the closed state and URL.
  useEffect(() => {
    if (selectedId === null) return;
    const onKeyDown = (event: KeyboardEvent) => {
      if (event.key === "Escape" && !event.defaultPrevented) {
        setSelected(null);
      }
    };
    document.addEventListener("keydown", onKeyDown);
    return () => {
      document.removeEventListener("keydown", onKeyDown);
    };
  }, [selectedId]); // setSelected is stable (navigate identity)
  const selectionAbsent =
    selectedId !== null &&
    findings.data !== undefined &&
    !findings.data.data.some((f) => f.finding_id === selectedId);

  return (
    <Page
      title="Findings"
      lead="Reconciliation verdicts with their resolution state — including destination-keyed orphans, which have no ledger record at all and can never appear as effect rows."
    >
      {findings.isPending ? (
        <div className="min-h-40" aria-busy="true" />
      ) : findings.isError ? (
        findings.error instanceof UnsupportedVersionError ? (
          <div className="max-w-2xl rounded-(--radius-structural) border border-border bg-layer-panel p-5">
            <p className="font-mono text-2xs font-medium tracking-wide text-text-tertiary uppercase">
              Unsupported payload version
            </p>
            <p className="mt-2 text-sm text-text-primary">{findings.error.message}</p>
          </div>
        ) : (
          <p className="font-mono text-xs text-text-secondary">{findings.error.message}</p>
        )
      ) : findings.data.data.length === 0 ? (
        <div className="max-w-2xl rounded-(--radius-structural) border border-border bg-layer-panel p-5">
          <p className="text-sm text-text-primary">
            No findings are recorded. Reconciliation has not produced a verdict for any effect —
            this is a statement about the ledger, not a claim that everything is safe.
          </p>
        </div>
      ) : (
        <>
          {selectionAbsent ? (
            <p
              className={
                "mb-3 max-w-2xl rounded-(--radius-structural) border border-border " +
                "bg-layer-workspace px-3 py-2 text-sm text-text-primary"
              }
            >
              The requested selection <span className="font-mono text-xs">{selectedId}</span> is
              not in the loaded findings; nothing is selected.
            </p>
          ) : null}
          <FindingsList
            findings={findings.data.data}
            selectedId={selectionAbsent ? null : selectedId}
            onSelect={setSelected}
          />
          <p className="mt-3 border-t border-border-subtle pt-2 text-xs text-text-tertiary">
            {findings.data.has_more
              ? `${findings.data.data.length} shown, more available`
              : `${findings.data.data.length} of ${findings.data.data.length}`}
            {" · as_of "}
            <span className="font-mono">{findings.data.as_of}</span>
          </p>
        </>
      )}
    </Page>
  );
}
