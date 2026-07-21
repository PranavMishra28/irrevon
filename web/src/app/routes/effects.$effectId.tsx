import { Link, createFileRoute, notFound } from "@tanstack/react-router";
import { useEffect } from "react";
import { isMockMode } from "@/app/data-mode";
import { ContextRail } from "@/features/effects/context-rail";
import {
  AttemptsSection,
  DecisionLogSection,
  IdentitySection,
  RawJsonSection,
  ReconciliationSection,
  ResynthesisSection,
} from "@/features/effects/evidence";
import { useEffectInspect, useEffectItem } from "@/features/effects/queries";
import { EffectTimeline } from "@/features/effects/timeline";
import { ConnectionsTable } from "@/features/graph/connections";
import { GraphNodeInspector, type InspectorPanel } from "@/features/graph/inspector";
import { GraphLegend } from "@/features/graph/legend";
import { buildEffectGraph } from "@/features/graph/model";
import { CausalGraph } from "@/features/graph/renderer";
import { NotFoundError, UnsupportedVersionError } from "@/shared/api/errors";
import { StatusTriplet } from "@/shared/domain/status/status-triplet";
import { EffectClassBadge } from "@/shared/domain/status/supporting-status";
import type { Lifecycle } from "@/shared/contracts/generated/state-model";
import type { ClassificationDisplay } from "@/shared/domain/status/taxonomy";
import { getSingleKeyShortcutsEnabled } from "@/shared/lib/prefs";
import { truncateEffectId } from "@/shared/lib/ids";
import { Copy } from "@/shared/ui/icons";
import { useAnnouncer } from "@/shared/ui/layout/live-regions";
import { IconButton } from "@/shared/ui/primitives/button";
import { useMediaQuery } from "@/shared/ui/use-media";

const EFFECT_ID_RE = /^[0-9a-f]{64}$/;
const NODE_ID_RE = /^node:[a-z-]+:[\w.:-]+$/;

type View = "graph" | "timeline" | "evidence" | "context" | "raw";
const VIEWS: readonly View[] = ["graph", "timeline", "evidence", "context", "raw"];
const PANELS: readonly InspectorPanel[] = ["summary", "evidence", "history"];

interface DetailSearch {
  view?: View;
  selected?: string;
  panel?: InspectorPanel;
}

/**
 * The investigation surface (REDESIGN-BRIEF §5.4): source-derived title
 * block, causal graph + selected-node inspector on top, and the proven
 * Timeline/Evidence/Context plane below. Graph, timeline, and inspector
 * share `selected` URL state. Everything rendered comes from the inspect
 * payload and Q1 record view — no derived scores, no recommendations, no
 * mutating control.
 */
export const Route = createFileRoute("/effects/$effectId")({
  validateSearch: (search: Record<string, unknown>): DetailSearch => {
    const out: DetailSearch = {};
    if (typeof search.view === "string" && (VIEWS as readonly string[]).includes(search.view)) {
      if (search.view !== "graph") out.view = search.view as View;
    }
    if (typeof search.selected === "string" && NODE_ID_RE.test(search.selected)) {
      out.selected = search.selected;
    }
    if (
      typeof search.panel === "string" &&
      (PANELS as readonly string[]).includes(search.panel)
    ) {
      if (search.panel !== "summary") out.panel = search.panel as InspectorPanel;
    }
    return out;
  },
  beforeLoad: ({ params }) => {
    if (!EFFECT_ID_RE.test(params.effectId)) throw notFound();
  },
  component: EffectDetailPage,
});

function Region({ title, children }: { title: string; children: React.ReactNode }) {
  return (
    <section className="min-w-0">
      <h2 className="border-b border-border pb-2 font-mono text-2xs font-medium tracking-wide text-text-tertiary uppercase">
        {title}
      </h2>
      <div className="pt-3">{children}</div>
    </section>
  );
}

function EffectDetailPage() {
  const { effectId } = Route.useParams();
  const rawSearch = Route.useSearch();
  // Re-apply the typed contract (parent search passthrough can leak raw values).
  const search: DetailSearch = { ...rawSearch };
  if (search.view !== undefined && !VIEWS.includes(search.view)) delete search.view;
  if (search.selected !== undefined && !NODE_ID_RE.test(search.selected)) {
    delete search.selected;
  }
  if (search.panel !== undefined && !PANELS.includes(search.panel)) delete search.panel;
  const navigate = Route.useNavigate();
  const { announce } = useAnnouncer();
  const inspect = useEffectInspect(effectId);
  const item = useEffectItem(effectId);
  const isMobile = !useMediaQuery("(min-width: 768px)");
  const horizontal = useMediaQuery("(min-width: 1024px)");
  const view = search.view ?? "graph";
  const panel = search.panel ?? "summary";

  const setSearchPart = (next: {
    view?: View | undefined;
    selected?: string | undefined;
    panel?: InspectorPanel | undefined;
  }) => {
    void navigate({
      search: (prev: DetailSearch) => {
        const merged = { ...prev, ...next };
        if (merged.view === "graph" || merged.view === undefined) delete merged.view;
        if (merged.panel === "summary" || merged.panel === undefined) delete merged.panel;
        if (merged.selected === undefined) delete merged.selected;
        return merged as DetailSearch;
      },
      replace: true,
    });
  };

  const setSelected = (nodeId: string | null) => {
    setSearchPart({ selected: nodeId ?? undefined });
    if (nodeId !== null) announce("1 node selected");
  };

  // `t`/`g` projection shortcuts (single-key shortcuts only).
  useEffect(() => {
    const onKey = (event: KeyboardEvent) => {
      if (event.metaKey || event.ctrlKey || event.altKey) return;
      const target = event.target;
      if (
        target instanceof HTMLElement &&
        (target.isContentEditable || ["INPUT", "TEXTAREA", "SELECT"].includes(target.tagName))
      ) {
        return;
      }
      if (!getSingleKeyShortcutsEnabled()) return;
      if (event.key === "t") setSearchPart({ view: "timeline" });
      else if (event.key === "g") setSearchPart({ view: "graph" });
    };
    window.addEventListener("keydown", onKey);
    return () => {
      window.removeEventListener("keydown", onKey);
    };
    // setSearchPart wraps the stable navigate identity
  }, []);

  const copyId = () => {
    void navigator.clipboard.writeText(effectId).then(() => {
      announce("Effect ID copied");
    });
  };

  if (inspect.isError && inspect.error instanceof NotFoundError) {
    return (
      <div className="mx-auto w-full max-w-2xl px-6 py-10">
        <h1
          tabIndex={-1}
          data-route-heading
          className="text-xl font-semibold text-text-primary"
        >
          No exact match
        </h1>
        <p className="mt-2 text-sm text-text-secondary">
          No ledger record is addressed by{" "}
          <span className="font-mono text-xs break-all">{effectId}</span>. The workbench does
          not guess — an unknown id is not treated as a possible orphan.
        </p>
        <Link
          to="/effects"
          className="mt-4 inline-flex h-8 items-center rounded-(--radius-control) border border-border bg-layer-panel px-3 text-sm font-medium text-text-primary hover:bg-(--sys-state-hover)"
        >
          Go to Effects
        </Link>
      </div>
    );
  }

  if (inspect.isError) {
    const unsupported = inspect.error instanceof UnsupportedVersionError;
    return (
      <div className="mx-auto w-full max-w-2xl px-6 py-10">
        <h1
          tabIndex={-1}
          data-route-heading
          className="text-xl font-semibold text-text-primary"
        >
          {unsupported ? "Unsupported payload version" : "Read failed"}
        </h1>
        <p className="mt-2 font-mono text-xs text-text-secondary">{inspect.error.message}</p>
      </div>
    );
  }

  const payload = inspect.data;
  const record = item.data?.record;
  const model = payload
    ? buildEffectGraph({ inspect: payload, ...(record ? { record } : {}) })
    : null;

  const selectedNode =
    model && search.selected !== undefined
      ? (model.nodes.find((n) => n.id === search.selected) ?? null)
      : null;
  const selectionAbsent =
    search.selected !== undefined && model !== null && selectedNode === null;

  const graphWorkspace = model ? (
    <div className="grid grid-cols-1 gap-4 min-[1120px]:grid-cols-12">
      <div
        className={
          "min-w-0 rounded-(--radius-structural) border border-border bg-layer-workspace " +
          "p-3 min-[1120px]:col-span-8"
        }
      >
        {selectionAbsent ? (
          <p className="mb-2 rounded-(--radius-structural) border border-border bg-layer-panel px-3 py-1.5 text-sm text-text-primary">
            The requested selection is absent from this graph; nothing is selected.
          </p>
        ) : null}
        <CausalGraph
          model={model}
          orientation={horizontal ? "horizontal" : "vertical"}
          selected={selectedNode?.id ?? null}
          onSelect={setSelected}
        />
      </div>
      <div className="flex min-w-0 flex-col gap-4 min-[1120px]:col-span-4">
        {selectedNode ? (
          <GraphNodeInspector
            model={model}
            node={selectedNode}
            panel={panel}
            onPanelChange={(next) => {
              setSearchPart({ panel: next });
            }}
            onClose={() => {
              setSelected(null);
            }}
            pivots={
              selectedNode.kind === "adapter"
                ? [
                    {
                      label: `Filter Effects by adapter ${selectedNode.primary}`,
                      href: `/effects`,
                    },
                  ]
                : []
            }
          />
        ) : (
          <section
            aria-label="Selected node"
            className="rounded-(--radius-structural) border border-border-subtle bg-layer-panel p-(--dt-panel-pad) text-sm text-text-secondary shadow-(--sys-edge-light)"
          >
            No node selected. Select a graph node (or a timeline event) to open its cited
            evidence here.
          </section>
        )}
        <GraphLegend />
      </div>
      <div className="min-w-0 min-[1120px]:col-span-12">
        <ConnectionsTable model={model} />
      </div>
    </div>
  ) : null;

  const timelineRegion = payload ? (
    <Region title="Timeline">
      <EffectTimeline
        payload={payload}
        selectedNodeId={selectedNode?.id ?? null}
        onSelectNode={(nodeId) => {
          setSelected(nodeId);
        }}
      />
    </Region>
  ) : null;

  const evidenceRegion = payload ? (
    <Region title="Evidence">
      <div className="flex flex-col gap-4">
        <IdentitySection payload={payload} record={record} />
        <AttemptsSection payload={payload} />
        <ReconciliationSection payload={payload} />
        <ResynthesisSection payload={payload} record={record} />
        <DecisionLogSection payload={payload} />
        {!isMobile ? <RawJsonSection payload={payload} /> : null}
      </div>
    </Region>
  ) : null;

  const contextRegion = payload ? (
    <Region title="Context">
      <ContextRail payload={payload} record={record} />
    </Region>
  ) : null;

  return (
    <div className="mx-auto w-full max-w-[1600px] px-4 py-5 min-[768px]:px-6">
      {/* Title block (§3.4 role 9): designation line, source-derived title,
          then the double hairline rule. Detail routes only. */}
      <header>
        <nav aria-label="Breadcrumb" className="text-xs text-text-tertiary">
          <Link to="/effects" className="hover:text-text-primary hover:underline">
            Effects
          </Link>
          <span aria-hidden> / </span>
          <span className="machine-id font-mono">{truncateEffectId(effectId)}</span>
        </nav>
        <p className="mt-3 flex flex-wrap items-center gap-x-2 font-mono text-2xs font-medium tracking-[0.08em] text-text-tertiary uppercase">
          <span>
            EFFECT · <span className="normal-case">{truncateEffectId(effectId)}</span>
          </span>
          {payload ? <span className="normal-case">· {payload.record.adapter_id}</span> : null}
          <IconButton label="Copy effect id" onClick={copyId}>
            <Copy size={12} />
          </IconButton>
        </p>
        <h1
          tabIndex={-1}
          data-route-heading
          className="mt-0.5 text-(length:--sys-text-display) leading-(--sys-leading-display) font-semibold tracking-[-0.015em] text-text-primary"
        >
          {payload
            ? `${payload.record.effect_type} · ${payload.record.scope}`
            : "Investigation"}
        </h1>
        <details className="mt-1 max-w-full">
          <summary className="cursor-default text-2xs text-text-tertiary select-none">
            Full effect id
          </summary>
          <p className="machine-id font-mono text-xs break-all text-text-primary">{effectId}</p>
        </details>
        {payload ? (
          <div className="mt-2 flex flex-wrap items-center gap-x-5 gap-y-2">
            <EffectClassBadge value={payload.record.effect_class} />
            <StatusTriplet
              lifecycle={payload.record.lifecycle as Lifecycle}
              classification={payload.classification as ClassificationDisplay}
              resolution={latestOpenResolution(payload)}
              excessEffectCount={payload.findings[0]?.excess_effect_count ?? undefined}
            />
            <span className="ml-auto text-2xs text-text-tertiary">
              data mode <span className="font-mono">{isMockMode ? "mock" : "live"}</span>
            </span>
          </div>
        ) : null}
        <div aria-hidden className="mt-3">
          <div className="border-t border-border" />
          <div className="mt-px border-t border-border-subtle" />
        </div>
        <p className="mt-1">
          <a href="#causal-graph" className="text-2xs text-accent underline underline-offset-2">
            Skip to graph
          </a>
        </p>
      </header>

      {payload ? (
        isMobile ? (
          <div className="mt-4">
            <div
              role="tablist"
              aria-label="Investigation projections"
              className="flex overflow-x-auto border-b border-border"
            >
              {VIEWS.map((v) => (
                <button
                  key={v}
                  type="button"
                  role="tab"
                  aria-selected={view === v}
                  tabIndex={view === v ? 0 : -1}
                  onClick={() => {
                    setSearchPart({ view: v });
                  }}
                  onKeyDown={(event) => {
                    if (event.key === "ArrowRight" || event.key === "ArrowLeft") {
                      event.preventDefault();
                      const index = VIEWS.indexOf(v);
                      const next =
                        VIEWS[
                          (index + (event.key === "ArrowRight" ? 1 : VIEWS.length - 1)) %
                            VIEWS.length
                        ];
                      if (next) setSearchPart({ view: next });
                    }
                  }}
                  className={
                    "min-h-11 shrink-0 border-b-2 px-3 text-sm font-medium capitalize " +
                    (view === v
                      ? "border-(--color-accent) text-text-primary"
                      : "border-transparent text-text-secondary")
                  }
                >
                  {v}
                </button>
              ))}
            </div>
            <div id="causal-graph" className="mt-4">
              {view === "graph" ? graphWorkspace : null}
              {view === "timeline" ? timelineRegion : null}
              {view === "evidence" ? evidenceRegion : null}
              {view === "context" ? contextRegion : null}
              {view === "raw" ? (
                <Region title="Raw">
                  <RawJsonSection payload={payload} />
                </Region>
              ) : null}
            </div>
          </div>
        ) : (
          <>
            <div id="causal-graph" className="mt-4">
              {graphWorkspace}
            </div>
            <div className="mt-6 grid grid-cols-1 gap-6 min-[1024px]:grid-cols-12">
              <div className="min-[1024px]:col-span-4">{timelineRegion}</div>
              <div className="min-[1024px]:col-span-8 min-[1440px]:col-span-5">
                {evidenceRegion}
              </div>
              <div className="min-[1024px]:col-span-12 min-[1440px]:col-span-3">
                {contextRegion}
              </div>
            </div>
          </>
        )
      ) : (
        <div className="mt-5 min-h-64" aria-busy="true" />
      )}
    </div>
  );
}

function latestOpenResolution(payload: {
  findings: { finding_id: number }[];
  resolutions: { finding_id: number; to_status: string }[];
}) {
  const finding = payload.findings[payload.findings.length - 1];
  if (!finding) return undefined;
  const chain = payload.resolutions.filter((r) => r.finding_id === finding.finding_id);
  const last = chain[chain.length - 1];
  return (last?.to_status ??
    "OPEN") as import("@/shared/contracts/generated/state-model").ResolutionStatus;
}
