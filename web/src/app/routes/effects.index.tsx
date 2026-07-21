import { createFileRoute } from "@tanstack/react-router";
import { useEffect, useRef, useState } from "react";
import { EffectCards } from "@/features/effects/effect-cards";
import { EffectsGrid } from "@/features/effects/effects-grid";
import { EffectsFilterBar } from "@/features/effects/filter-bar";
import { useEffectsQuery } from "@/features/effects/queries";
import { EffectRowInspector } from "@/features/effects/row-inspector";
import { parseEffectsSearch, type EffectsSearch } from "@/shared/api/filters";
import { UnsupportedVersionError } from "@/shared/api/errors";
import { Button } from "@/shared/ui/primitives/button";
import { Dialog } from "@/shared/ui/primitives/dialog";
import { Page } from "@/shared/ui/layout/page";
import { useMediaQuery } from "@/shared/ui/use-media";

/**
 * Effects — the principal working surface (REDESIGN-BRIEF §5.3, ruling A1).
 * One list projection: full table ≥1120 with a docked single-effect
 * inspector via `?inspect=`, record cards below 1120. There is deliberately
 * NO multi-effect graph mode: no served contract field supports a
 * cross-effect edge; graph interaction begins only after selecting one
 * effect and opening its causal investigation.
 */
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
        <div key={i} className="h-(--dt-row-h) animate-pulse rounded-none bg-layer-sunken" />
      ))}
    </div>
  );
}

const INSPECT_SHAPE = /^[0-9a-f]{64}$/;

function EffectsPage() {
  const rawSearch = Route.useSearch();
  // Root-route search passthrough can leak unvalidated params; re-apply the
  // typed contract here so an invalid `inspect` is dropped, never guessed.
  const search: EffectsSearch = { ...rawSearch };
  if (search.inspect !== undefined && !INSPECT_SHAPE.test(search.inspect)) {
    delete search.inspect;
  }
  const navigate = Route.useNavigate();
  const query = useEffectsQuery(search);
  const filterRef = useRef<HTMLInputElement>(null);
  const isDesktop = useMediaQuery("(min-width: 1120px)");
  const [filterSheetOpen, setFilterSheetOpen] = useState(false);

  const setSearch = (next: EffectsSearch) => {
    void navigate({ search: next });
  };

  const setInspect = (effectId: string | null) => {
    const next = { ...search };
    if (effectId === null) delete next.inspect;
    else next.inspect = effectId;
    void navigate({ search: next, replace: true });
  };

  const hasFilters =
    (search.lifecycle?.length ?? 0) > 0 ||
    (search.classification?.length ?? 0) > 0 ||
    search.effect_type !== undefined;

  const inspectedItem =
    search.inspect !== undefined && query.data
      ? (query.data.data.find((item) => item.record.effect_id === search.inspect) ?? null)
      : null;

  let body: React.ReactNode;
  if (query.isPending) {
    body = <GridSkeleton />;
  } else if (query.isError) {
    body =
      query.error instanceof UnsupportedVersionError ? (
        <div className="mt-4 rounded-(--radius-structural) border border-border bg-layer-panel p-5">
          <p className="font-mono text-2xs font-medium tracking-wide text-text-tertiary uppercase">
            Unsupported payload version
          </p>
          <p className="mt-2 text-sm text-text-primary">{query.error.message}</p>
          <p className="mt-1 text-sm text-text-secondary">
            Domain data is not rendered under an unknown contract version.
          </p>
        </div>
      ) : (
        <div className="mt-4 rounded-(--radius-structural) border border-border bg-layer-panel p-5">
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
      <div className="mt-4 rounded-(--radius-structural) border border-border bg-layer-panel p-5">
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
      <div className="mt-4 rounded-(--radius-structural) border border-border bg-layer-panel p-5">
        <p className="text-sm text-text-primary">
          No ledger records exist. This does not mean “all safe” — nothing has been registered
          yet.
        </p>
      </div>
    );
  } else {
    const footer = (
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
    );
    body = isDesktop ? (
      <div className="flex items-start gap-4">
        <div className="min-w-0 flex-1">
          <div
            role="group"
            aria-label="Effects table, scroll horizontally if needed"
            tabIndex={-1}
            className="overflow-x-auto rounded-(--radius-structural) border border-border bg-layer-workspace"
          >
            <EffectsGrid
              items={query.data.data}
              filterRef={filterRef}
              inspectedId={search.inspect ?? null}
              onInspect={setInspect}
            />
          </div>
          {footer}
        </div>
        {search.inspect !== undefined ? (
          <div className="w-[440px] shrink-0">
            {inspectedItem ? (
              <EffectRowInspector
                item={inspectedItem}
                onClose={() => {
                  setInspect(null);
                }}
              />
            ) : (
              <section
                data-testid="effect-row-inspector"
                aria-label="Effect inspector"
                className="rounded-(--radius-structural) border border-border-subtle bg-layer-panel p-(--dt-panel-pad) shadow-(--sys-edge-light)"
              >
                <p className="text-sm text-text-primary">
                  The requested effect{" "}
                  <span className="machine-id font-mono text-xs break-all">
                    {search.inspect}
                  </span>{" "}
                  is not in the loaded snapshot. Nothing is selected — an unknown id is not
                  treated as a possible record.
                </p>
                <Button
                  className="mt-3"
                  onClick={() => {
                    setInspect(null);
                  }}
                >
                  Clear
                </Button>
              </section>
            )}
          </div>
        ) : null}
      </div>
    ) : (
      <>
        <EffectCards items={query.data.data} />
        {footer}
      </>
    );
  }

  const activeFilterChips = [
    ...(search.lifecycle ?? []).map((value) => ({ kind: "lifecycle" as const, value })),
    ...(search.classification ?? []).map((value) => ({
      kind: "classification" as const,
      value,
    })),
    ...(search.effect_type !== undefined
      ? [{ kind: "effect_type" as const, value: search.effect_type }]
      : []),
  ];

  return (
    <Page
      title="Effects"
      lead="Every registered effect record. Lifecycle, reconciliation classification, and resolution are three separate columns answering three different questions."
    >
      {isDesktop ? (
        <EffectsFilterBar
          search={search}
          onChange={setSearch}
          firstControlRef={filterRef}
          resultCount={query.data?.data.length}
        />
      ) : (
        <div className="flex flex-wrap items-center gap-2 border-b border-border-subtle pb-3">
          <Button
            onClick={() => {
              setFilterSheetOpen(true);
            }}
            aria-haspopup="dialog"
          >
            Filters{activeFilterChips.length > 0 ? ` (${activeFilterChips.length})` : ""}
          </Button>
          {activeFilterChips.map((chip) => (
            <button
              key={`${chip.kind}:${chip.value}`}
              type="button"
              onClick={() => {
                const next: EffectsSearch = { ...search };
                if (chip.kind === "lifecycle") {
                  next.lifecycle = (next.lifecycle ?? []).filter((v) => v !== chip.value);
                  if (next.lifecycle.length === 0) delete next.lifecycle;
                } else if (chip.kind === "classification") {
                  next.classification = (next.classification ?? []).filter(
                    (v) => v !== chip.value,
                  );
                  if (next.classification.length === 0) delete next.classification;
                } else {
                  delete next.effect_type;
                }
                setSearch(next);
              }}
              className={
                "flex h-7 items-center gap-1 rounded-(--radius-control) border border-accent " +
                "bg-accent-bg px-2 font-mono text-2xs font-medium tracking-wide " +
                "text-text-primary uppercase"
              }
            >
              {chip.value}
              <span aria-hidden>×</span>
              <span className="sr-only">Remove {chip.kind} filter</span>
            </button>
          ))}
          <span className="ml-auto text-xs text-text-tertiary">
            {query.data === undefined ? "" : `${query.data.data.length} shown`}
          </span>
          <Dialog
            open={filterSheetOpen}
            onOpenChange={setFilterSheetOpen}
            title="Filters"
            description="Exact contract filters; results update as you toggle."
          >
            <EffectsFilterBar
              search={search}
              onChange={setSearch}
              firstControlRef={filterRef}
              resultCount={query.data?.data.length}
            />
          </Dialog>
        </div>
      )}
      <div className="mt-1">{body}</div>
    </Page>
  );
}
