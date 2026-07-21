import { createFileRoute } from "@tanstack/react-router";
import { useEffect, useRef, useState } from "react";
import { EffectsGrid } from "@/features/effects/effects-grid";
import { EffectsFilterBar } from "@/features/effects/filter-bar";
import { useEffectsQuery } from "@/features/effects/queries";
import { parseEffectsSearch, type EffectsSearch } from "@/shared/api/filters";
import { UnsupportedVersionError } from "@/shared/api/errors";
import { Button } from "@/shared/ui/primitives/button";
import { Page } from "@/shared/ui/layout/page";

export const Route = createFileRoute("/effects/")({
  validateSearch: (search: Record<string, unknown>): EffectsSearch =>
    parseEffectsSearch(search),
  component: EffectsPage,
});

/** Layout-faithful skeleton, shown only after 150 ms (no spinner for local reads). */
function GridSkeleton() {
  const [visible, setVisible] = useState(false);
  useEffect(() => {
    const timer = setTimeout(() => {
      setVisible(true);
    }, 150);
    return () => {
      clearTimeout(timer);
    };
  }, []);
  if (!visible) return <div className="min-h-64" />;
  return (
    <div aria-hidden className="flex min-h-64 flex-col gap-px pt-2">
      {Array.from({ length: 7 }, (_, i) => (
        <div key={i} className="h-(--dt-row-h) animate-pulse rounded-none bg-surface-2" />
      ))}
    </div>
  );
}

function EffectsPage() {
  const search = Route.useSearch();
  const navigate = Route.useNavigate();
  const query = useEffectsQuery(search);
  const filterRef = useRef<HTMLInputElement>(null);

  const setSearch = (next: EffectsSearch) => {
    void navigate({ search: next });
  };

  const hasFilters =
    (search.lifecycle?.length ?? 0) > 0 ||
    (search.classification?.length ?? 0) > 0 ||
    search.effect_type !== undefined;

  let body: React.ReactNode;
  if (query.isPending) {
    body = <GridSkeleton />;
  } else if (query.isError) {
    body =
      query.error instanceof UnsupportedVersionError ? (
        <div className="mt-4 rounded-(--radius-structural) border border-border bg-surface-1 p-5">
          <p className="font-mono text-2xs font-medium tracking-wide text-text-tertiary uppercase">
            Unsupported payload version
          </p>
          <p className="mt-2 text-sm text-text-primary">{query.error.message}</p>
          <p className="mt-1 text-sm text-text-secondary">
            Domain data is not rendered under an unknown contract version.
          </p>
        </div>
      ) : (
        <div className="mt-4 rounded-(--radius-structural) border border-border bg-surface-1 p-5">
          <p className="font-mono text-xs text-text-secondary">
            {query.error.name}: {query.error.message}
          </p>
          <Button
            className="mt-3"
            onClick={() => {
              void query.refetch();
            }}
          >
            Retry
          </Button>
        </div>
      );
  } else if (query.data.data.length === 0 && hasFilters) {
    body = (
      <div className="mt-4 rounded-(--radius-structural) border border-border bg-surface-1 p-5">
        <p className="text-sm text-text-primary">No effects match these filters.</p>
        <Button
          variant="ghost"
          className="mt-2"
          onClick={() => {
            setSearch({});
          }}
        >
          Clear filters
        </Button>
      </div>
    );
  } else if (query.data.data.length === 0) {
    body = (
      <div className="mt-4 rounded-(--radius-structural) border border-border bg-surface-1 p-5">
        <p className="text-sm text-text-primary">
          No ledger records exist. This does not mean “all safe” — nothing has been registered
          yet.
        </p>
      </div>
    );
  } else {
    body = (
      <>
        <EffectsGrid items={query.data.data} filterRef={filterRef} />
        <div className="flex items-center justify-between border-t border-border-subtle py-2">
          <span className="text-xs text-text-tertiary">
            {query.data.has_more
              ? `${query.data.data.length} shown, more available`
              : `${query.data.data.length} of ${query.data.data.length}`}
            {" · as_of "}
            <span className="font-mono">{query.data.as_of}</span>
          </span>
          {query.data.has_more && query.data.next_cursor !== null ? (
            <Button
              onClick={() => {
                setSearch({ ...search, cursor: query.data.next_cursor ?? "" });
              }}
            >
              Next page
            </Button>
          ) : null}
        </div>
      </>
    );
  }

  return (
    <Page
      title="Effects"
      lead="Every registered effect record. Lifecycle, reconciliation classification, and resolution are three separate columns answering three different questions."
    >
      <EffectsFilterBar
        search={search}
        onChange={setSearch}
        firstControlRef={filterRef}
        resultCount={query.data?.data.length}
      />
      <div className="mt-1">{body}</div>
    </Page>
  );
}
