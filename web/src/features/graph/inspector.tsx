import { useAnnouncer } from "@/shared/ui/layout/live-regions";
import { Copy, X } from "@/shared/ui/icons";
import { IconButton } from "@/shared/ui/primitives/button";
import { PanelHeader, SunkenWell } from "@/shared/ui/primitives/panel";
import type { GraphModel, GraphNode } from "./model";
import { truncateGraphValue } from "./render-utils";

/**
 * Selected-node detail rail (REDESIGN-BRIEF §4.4): Summary, Evidence,
 * History projections over the selected node's cited facts. Values support
 * copy and contracted pivots only — there is no mutation menu anywhere.
 */

export type InspectorPanel = "summary" | "evidence" | "history";

const PANELS: readonly { id: InspectorPanel; label: string }[] = [
  { id: "summary", label: "Summary" },
  { id: "evidence", label: "Evidence" },
  { id: "history", label: "History" },
];

export function GraphNodeInspector({
  model,
  node,
  panel,
  onPanelChange,
  onClose,
  pivots,
}: {
  model: GraphModel;
  node: GraphNode;
  panel: InspectorPanel;
  onPanelChange: (panel: InspectorPanel) => void;
  onClose: () => void;
  /** Contracted pivots (e.g. filter Effects by exact adapter). */
  pivots?: { label: string; href: string }[];
}) {
  const { announce } = useAnnouncer();
  const relatedEdges = model.edges.filter((e) => e.from === node.id || e.to === node.id);
  const names = new Map(
    model.nodes.map((n) => [n.id, `${n.kindLabel} ${truncateGraphValue(n.primary)}`]),
  );

  const copyValue = (label: string, value: string) => {
    void navigator.clipboard.writeText(value).then(() => {
      announce(`${label} copied`);
    });
  };

  return (
    <section
      aria-label={`Selected node: ${node.kindLabel}`}
      data-testid="graph-inspector"
      className={
        "flex min-w-0 flex-col rounded-(--radius-structural) border border-border-subtle " +
        "bg-layer-panel shadow-(--sys-edge-light)"
      }
    >
      <PanelHeader
        title={node.kindLabel}
        meta={truncateGraphValue(node.primary)}
        actions={
          <IconButton label="Clear selection" onClick={onClose}>
            <X size={14} />
          </IconButton>
        }
      />
      <div
        role="tablist"
        aria-label="Node projections"
        className="flex border-b border-border-subtle px-2"
      >
        {PANELS.map((p) => (
          <button
            key={p.id}
            type="button"
            role="tab"
            id={`graph-panel-tab-${p.id}`}
            aria-selected={panel === p.id}
            aria-controls={`graph-panel-${p.id}`}
            tabIndex={panel === p.id ? 0 : -1}
            onClick={() => {
              onPanelChange(p.id);
            }}
            onKeyDown={(event) => {
              const index = PANELS.findIndex((x) => x.id === p.id);
              if (event.key === "ArrowRight" || event.key === "ArrowLeft") {
                event.preventDefault();
                const next =
                  PANELS[
                    (index + (event.key === "ArrowRight" ? 1 : PANELS.length - 1)) %
                      PANELS.length
                  ];
                if (next) {
                  onPanelChange(next.id);
                  document.getElementById(`graph-panel-tab-${next.id}`)?.focus();
                }
              }
            }}
            className={
              "border-b-2 px-2.5 py-1.5 text-xs font-medium " +
              (panel === p.id
                ? "border-(--color-accent) text-text-primary"
                : "border-transparent text-text-secondary hover:text-text-primary")
            }
          >
            {p.label}
          </button>
        ))}
      </div>

      <div
        role="tabpanel"
        id={`graph-panel-${panel}`}
        aria-labelledby={`graph-panel-tab-${panel}`}
        className="flex min-w-0 flex-col gap-2 p-(--dt-panel-pad)"
      >
        {panel === "summary" ? (
          <>
            <dl className="grid grid-cols-[max-content_1fr] gap-x-3 gap-y-1">
              <dt className="font-mono text-2xs tracking-wide text-text-tertiary uppercase">
                Kind
              </dt>
              <dd className="text-xs text-text-primary">{node.kindLabel}</dd>
              <dt className="font-mono text-2xs tracking-wide text-text-tertiary uppercase">
                Value
              </dt>
              <dd className="machine-id flex min-w-0 items-baseline gap-1 font-mono text-xs break-all text-text-primary">
                {node.primary}
                <IconButton
                  label={`Copy ${node.kindLabel} value`}
                  onClick={() => {
                    copyValue(node.kindLabel, node.primary);
                  }}
                >
                  <Copy size={12} />
                </IconButton>
              </dd>
              <dt className="font-mono text-2xs tracking-wide text-text-tertiary uppercase">
                Source
              </dt>
              <dd className="machine-id font-mono text-2xs break-all text-text-tertiary">
                {node.sourcePath}
              </dd>
            </dl>
            {node.absenceText !== undefined ? (
              <p className="text-sm text-text-secondary">{node.absenceText}</p>
            ) : null}
            {node.unrecognized ? (
              <p className="font-mono text-2xs text-text-secondary">
                unrecognized value — rendered verbatim, never coerced to a known kind
              </p>
            ) : null}
            {pivots && pivots.length > 0 ? (
              <div className="flex flex-wrap gap-2 border-t border-border-subtle pt-2">
                {pivots.map((pivot) => (
                  <a
                    key={pivot.href}
                    href={pivot.href}
                    className="text-xs text-accent underline underline-offset-2"
                  >
                    {pivot.label}
                  </a>
                ))}
              </div>
            ) : null}
          </>
        ) : null}

        {panel === "evidence" ? (
          <SunkenWell>
            <dl className="flex flex-col gap-1.5">
              {node.facts.map((fact) => (
                <div key={fact.path + fact.label} className="min-w-0">
                  <dt className="font-mono text-2xs text-text-tertiary">{fact.label}</dt>
                  <dd className="machine-id flex min-w-0 items-baseline gap-1 font-mono text-xs break-all text-text-primary">
                    {fact.value}
                    <IconButton
                      label={`Copy ${fact.label}`}
                      onClick={() => {
                        copyValue(fact.label, fact.value);
                      }}
                    >
                      <Copy size={12} />
                    </IconButton>
                  </dd>
                  <dd className="machine-id font-mono text-[10px] break-all text-text-tertiary">
                    {fact.path}
                  </dd>
                </div>
              ))}
            </dl>
          </SunkenWell>
        ) : null}

        {panel === "history" ? (
          <ul className="flex flex-col gap-1.5">
            {relatedEdges.length === 0 ? (
              <li className="text-sm text-text-secondary">No recorded connections.</li>
            ) : (
              relatedEdges.map((edge) => (
                <li key={edge.id} className="min-w-0">
                  <p className="machine-id font-mono text-2xs text-text-primary">
                    {names.get(edge.from)}{" "}
                    <span className="text-text-tertiary">—{edge.relation}→</span>{" "}
                    {names.get(edge.to)}
                  </p>
                  <p className="machine-id font-mono text-[10px] break-all text-text-tertiary">
                    {edge.evidencePath}
                  </p>
                </li>
              ))
            )}
          </ul>
        ) : null}
      </div>
    </section>
  );
}
