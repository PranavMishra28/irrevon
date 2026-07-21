import { useEffect, useRef, useState } from "react";
import type { KeyboardEvent } from "react";
import { FindingBadge } from "@/shared/domain/status/finding-badge";
import { LifecyclePill } from "@/shared/domain/status/lifecycle-pill";
import { ResolutionTag } from "@/shared/domain/status/resolution-tag";
import { TransportOutcomeInline } from "@/shared/domain/status/supporting-status";
import { CornerTicks } from "@/shared/ui/primitives/inspection-frame";
import type { GraphModel } from "./model";
import { layoutGraph, type Orientation, type PositionedNode } from "./layout";
import { ancestorPath, truncateGraphValue } from "./render-utils";

/**
 * Causal-graph renderer (REDESIGN-BRIEF §4.3–§4.4). HTML carries the nodes
 * and facts — each node is a positioned <button> with a contract-derived
 * accessible name; the SVG connector layer is aria-hidden decoration. DOM
 * order equals causal order. One roving tab stop; arrows walk causal order;
 * Enter/Space select; Escape clears. No pan, no drag, no free zoom.
 */

function NodeStatus({ status }: { status: NonNullable<PositionedNode["status"]> }) {
  switch (status.channel) {
    case "lifecycle":
      return <LifecyclePill value={status.value} />;
    case "classification":
      return <FindingBadge value={status.value} />;
    case "resolution":
      return <ResolutionTag value={status.value} />;
    case "transport":
      return <TransportOutcomeInline value={status.value} />;
  }
}

function nodeAccessibleName(node: PositionedNode): string {
  const parts = [node.kindLabel, truncateGraphValue(node.primary)];
  if (node.status) parts.push(`${node.status.channel} ${node.status.value}`);
  if (node.absenceText) parts.push(node.absenceText);
  if (node.unrecognized) parts.push("unrecognized value");
  return parts.join(", ");
}

export function CausalGraph({
  model,
  orientation,
  selected,
  onSelect,
  labelledBy,
}: {
  model: GraphModel;
  orientation: Orientation;
  selected: string | null;
  onSelect: (nodeId: string | null) => void;
  labelledBy?: string;
}) {
  const layout = layoutGraph(model, orientation);
  const containerRef = useRef<HTMLDivElement>(null);
  const selectedIndex = layout.nodes.findIndex((n) => n.id === selected);
  const [focusIndex, setFocusIndex] = useState(selectedIndex === -1 ? 0 : selectedIndex);

  // Keep the roving stop on the selected node when selection changes.
  useEffect(() => {
    if (selectedIndex !== -1) setFocusIndex(selectedIndex);
  }, [selectedIndex]);

  const path = selected !== null ? ancestorPath(model, selected) : null;

  const focusNode = (index: number) => {
    const next = Math.max(0, Math.min(layout.nodes.length - 1, index));
    setFocusIndex(next);
    requestAnimationFrame(() => {
      containerRef.current
        ?.querySelector<HTMLElement>(`[data-graph-node-index="${next}"]`)
        ?.focus();
    });
  };

  const onKeyDown = (event: KeyboardEvent<HTMLButtonElement>, index: number) => {
    switch (event.key) {
      case "ArrowRight":
      case "ArrowDown":
        event.preventDefault();
        focusNode(index + 1);
        break;
      case "ArrowLeft":
      case "ArrowUp":
        event.preventDefault();
        focusNode(index - 1);
        break;
      case "Home":
        event.preventDefault();
        focusNode(0);
        break;
      case "End":
        event.preventDefault();
        focusNode(layout.nodes.length - 1);
        break;
      case "Escape": {
        const node = layout.nodes[index];
        if (selected !== null && node) {
          event.preventDefault();
          event.stopPropagation();
          onSelect(null);
          focusNode(index);
        }
        break;
      }
      default:
        break;
    }
  };

  return (
    <div className="min-w-0">
      {model.integrityFailure ? (
        <p
          role="alert"
          className={
            "mb-3 rounded-(--radius-structural) border-2 border-border-strong " +
            "bg-layer-panel px-3 py-2 font-mono text-xs font-medium text-text-primary"
          }
        >
          LEDGER INTEGRITY INCIDENT — recomputed intent id does not match the stored effect id.
          The graph below renders the stored records verbatim; nothing is normalized.
        </p>
      ) : null}
      {model.notes.map((note) => (
        <p key={note} className="mb-2 font-mono text-2xs text-text-tertiary">
          {note}
        </p>
      ))}
      <div
        ref={containerRef}
        role="group"
        aria-label={
          labelledBy === undefined
            ? `Causal graph of effect ${model.effectId.slice(0, 12)}…; ${model.nodes.length} nodes; use arrow keys`
            : undefined
        }
        {...(labelledBy !== undefined ? { "aria-labelledby": labelledBy } : {})}
        data-testid="causal-graph"
        className="relative overflow-x-auto"
        style={{ minHeight: layout.height }}
      >
        <div className="relative" style={{ width: layout.width, height: layout.height }}>
          {/* Connector layer: decoration only; the Connections table is the twin. */}
          <svg
            aria-hidden
            className="absolute inset-0"
            width={layout.width}
            height={layout.height}
            viewBox={`0 0 ${layout.width} ${layout.height}`}
          >
            <defs>
              <marker
                id="dt-arrow"
                viewBox="0 0 8 8"
                refX="7"
                refY="4"
                markerWidth="7"
                markerHeight="7"
                orient="auto-start-reverse"
              >
                <path d="M0,0 L8,4 L0,8 z" className="fill-(--color-border-strong)" />
              </marker>
              <marker
                id="dt-arrow-accent"
                viewBox="0 0 8 8"
                refX="7"
                refY="4"
                markerWidth="7"
                markerHeight="7"
                orient="auto-start-reverse"
              >
                <path d="M0,0 L8,4 L0,8 z" className="fill-(--color-accent)" />
              </marker>
            </defs>
            {layout.annotations.map((annotation) =>
              annotation.kind === "notch" ? (
                <g key={annotation.id}>
                  <line
                    x1={annotation.x1}
                    y1={annotation.y1}
                    x2={annotation.x2}
                    y2={annotation.y2}
                    strokeWidth="2"
                    className="stroke-(--color-border-strong)"
                  />
                  {/* pawl wedge at the top of the boundary */}
                  <path
                    d={
                      layout.orientation === "horizontal"
                        ? `M${annotation.x1 - 5},${annotation.y1} h10 l-5,10 z`
                        : `M${annotation.x1},${annotation.y1 - 5} v10 l10,-5 z`
                    }
                    className="fill-(--color-border-strong)"
                  />
                </g>
              ) : (
                <line
                  key={annotation.id}
                  x1={annotation.x1}
                  y1={annotation.y1}
                  x2={annotation.x2}
                  y2={annotation.y2}
                  strokeWidth="1.5"
                  strokeDasharray="7 5"
                  className="stroke-(--color-border-strong)"
                />
              ),
            )}
            {layout.edges.map((edge) => {
              const emphasized = path?.edges.has(edge.id) ?? false;
              const strokeClass = emphasized
                ? "stroke-(--color-accent)"
                : "stroke-(--color-border-strong)";
              const dash =
                edge.stroke === "dashed"
                  ? "5 4"
                  : edge.stroke === "interrupted"
                    ? "2 7"
                    : undefined;
              // Short forward hops have no room for a readable label; the
              // Connections table below carries every relation verbatim.
              const gap = Math.abs(edge.x2 - edge.x1);
              const showLabel =
                layout.orientation === "vertical"
                  ? edge.x1 === edge.x2
                  : Math.abs(edge.y2 - edge.y1) > 8 || gap > 150;
              return (
                <g
                  key={edge.id}
                  className="transition-opacity duration-(--sys-dur-fast)"
                  opacity={path !== null && !emphasized ? 0.45 : 1}
                >
                  <line
                    x1={edge.x1}
                    y1={edge.y1}
                    x2={edge.x2}
                    y2={edge.y2}
                    strokeWidth="1.5"
                    strokeDasharray={dash}
                    className={strokeClass}
                    markerEnd={emphasized ? "url(#dt-arrow-accent)" : "url(#dt-arrow)"}
                  />
                  {edge.stroke === "interrupted" ? (
                    <text
                      x={edge.labelX}
                      y={edge.labelY + 14}
                      textAnchor="middle"
                      className="fill-(--color-text-secondary) font-mono"
                      fontSize="10"
                    >
                      ⌁
                    </text>
                  ) : null}
                  {showLabel ? (
                    <text
                      x={edge.labelX}
                      y={edge.labelY}
                      textAnchor="middle"
                      className="fill-(--color-text-tertiary) stroke-(--color-layer-workspace) font-mono"
                      fontSize="9"
                      strokeWidth="3"
                      paintOrder="stroke"
                    >
                      {edge.relation}
                    </text>
                  ) : null}
                </g>
              );
            })}
            {layout.annotations.map((annotation) => (
              <text
                key={`${annotation.id}-label`}
                x={layout.orientation === "horizontal" ? annotation.x1 : annotation.x1 + 2}
                y={layout.orientation === "horizontal" ? annotation.y2 + 26 : annotation.y1 - 6}
                textAnchor={layout.orientation === "horizontal" ? "middle" : "start"}
                className="fill-(--color-text-secondary) stroke-(--color-layer-workspace) font-mono"
                fontSize="9"
                strokeWidth="3"
                paintOrder="stroke"
              >
                {annotation.kind === "notch" ? "⟟ externalized" : `⌁ crash seam [EI]`}
              </text>
            ))}
          </svg>

          {/* Node layer: real DOM, causal order, roving tabindex. */}
          {layout.nodes.map((node, index) => {
            const isSelected = node.id === selected;
            const onPath = path?.nodes.has(node.id) ?? false;
            return (
              <button
                key={node.id}
                type="button"
                data-graph-node={node.id}
                data-graph-node-index={index}
                tabIndex={index === focusIndex ? 0 : -1}
                aria-pressed={isSelected}
                aria-label={nodeAccessibleName(node)}
                onKeyDown={(event) => {
                  onKeyDown(event, index);
                }}
                onFocus={() => {
                  setFocusIndex(index);
                }}
                onClick={() => {
                  onSelect(isSelected ? null : node.id);
                }}
                className={
                  "absolute flex flex-col items-start gap-0.5 overflow-hidden text-left " +
                  "rounded-(--radius-structural) border bg-layer-panel px-2 py-1.5 " +
                  "shadow-(--sys-edge-light) hover:bg-(--sys-state-hover) " +
                  (node.frame === "void" || node.frame === "dashed"
                    ? "border-dashed border-border "
                    : "border-border ") +
                  (node.frame === "void" ? "bg-transparent " : "") +
                  (node.hatched ? "dt-hatched " : "") +
                  (node.size === "gate" ? "items-center justify-center text-center " : "") +
                  (isSelected ? "dt-inspected " : "") +
                  (path !== null && !onPath ? "opacity-60 " : "")
                }
                style={{ left: node.x, top: node.y, width: node.w, height: node.h }}
              >
                {isSelected ? <CornerTicks /> : null}
                <span className="w-full truncate font-mono text-[10px] font-medium tracking-wide text-text-tertiary uppercase">
                  {node.kindLabel}
                </span>
                <span
                  className={
                    "machine-id w-full truncate font-mono text-xs " +
                    (node.absenceText !== undefined || node.frame === "void"
                      ? "text-text-secondary"
                      : "text-text-primary")
                  }
                >
                  {truncateGraphValue(node.primary)}
                </span>
                {node.status && node.size !== "compact" ? (
                  <NodeStatus status={node.status} />
                ) : null}
                {node.absenceText !== undefined && node.size !== "compact" ? (
                  <span className="w-full text-2xs leading-tight text-text-tertiary">
                    {node.absenceText}
                  </span>
                ) : null}
                {node.unrecognized ? (
                  <span className="font-mono text-[10px] text-text-secondary">
                    unrecognized value
                  </span>
                ) : null}
              </button>
            );
          })}
        </div>
      </div>
      <p className="mt-1 font-mono text-2xs text-text-tertiary" aria-live="polite">
        {selected !== null ? "1 node selected" : "no node selected"}
      </p>
    </div>
  );
}
