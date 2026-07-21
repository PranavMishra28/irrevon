import type { ReactNode } from "react";

/**
 * Layered surface primitives (REDESIGN-BRIEF §3.1). Six surface roles; the
 * seam treatment is information: L0→L1/L2 use `border`, L2→L3 and panel
 * internals use `border-subtle`, L5 is the only shadow layer. Dark-theme L3+
 * panels get the machined top-edge highlight (a no-op in light theme).
 */

type LayerRole = "nav" | "workspace" | "panel" | "overlay";

const LAYER_CLASSES: Record<LayerRole, string> = {
  nav: "bg-layer-nav border-border",
  workspace: "bg-layer-workspace border-border",
  panel: "bg-layer-panel border-border-subtle shadow-(--sys-edge-light)",
  overlay: "bg-layer-overlay border-border shadow-overlay",
};

export function Layer({
  surface,
  className = "",
  children,
}: {
  surface: LayerRole;
  className?: string;
  children?: ReactNode;
}) {
  return (
    <div
      className={`rounded-(--radius-structural) border ${LAYER_CLASSES[surface]} ${className}`}
    >
      {children}
    </div>
  );
}

/**
 * One grammar for every L3 panel header (REDESIGN-BRIEF §3.1/§1.5):
 * [TITLE sans sm 600] [META mono 2xs, ·-separated] [spacer] [ACTIONS].
 * Title never truncates — meta truncates first. No background: the panel
 * fill shows through. Height is a density token.
 */
export function PanelHeader({
  title,
  meta,
  actions,
  as: Heading = "h2",
}: {
  title: string;
  meta?: ReactNode;
  actions?: ReactNode;
  as?: "h2" | "h3" | "h4" | undefined;
}) {
  return (
    <div className="flex h-(--dt-panel-header-h) shrink-0 items-center gap-3 border-b border-border-subtle px-(--dt-panel-pad)">
      <Heading className="shrink-0 text-sm font-semibold text-text-primary">{title}</Heading>
      {meta ? (
        <span className="min-w-0 truncate font-mono text-2xs text-text-tertiary">{meta}</span>
      ) : null}
      {actions ? (
        <span className="ml-auto flex shrink-0 items-center gap-1">{actions}</span>
      ) : null}
    </div>
  );
}

/** An L3 panel: header grammar + padded body on the panel layer. */
export function Panel({
  title,
  meta,
  actions,
  children,
  className = "",
  bodyClassName,
  as,
}: {
  title: string;
  meta?: ReactNode;
  actions?: ReactNode;
  children: ReactNode;
  className?: string;
  bodyClassName?: string;
  as?: "h2" | "h3" | "h4";
}) {
  return (
    <section
      className={
        "flex min-w-0 flex-col rounded-(--radius-structural) border border-border-subtle " +
        "bg-layer-panel shadow-(--sys-edge-light) " +
        className
      }
    >
      <PanelHeader title={title} meta={meta} actions={actions} as={as} />
      <div className={bodyClassName ?? "min-w-0 p-(--dt-panel-pad)"}>{children}</div>
    </section>
  );
}

/**
 * Sunken well: code, raw JSON, empty slots, input troughs. Not an elevation
 * layer — the one surface darker than canvas. Raw content scrolls only
 * inside the well, never at body level; dense mode keeps ≥8px inner padding.
 */
export function SunkenWell({
  children,
  className = "",
  scrollX = false,
}: {
  children: ReactNode;
  className?: string;
  scrollX?: boolean;
}) {
  return (
    <div
      className={
        "min-w-0 rounded-(--radius-structural) border border-border-subtle bg-layer-sunken " +
        "p-(--dt-panel-pad) [padding:max(8px,calc(var(--dt-panel-pad)*0.75))] " +
        (scrollX ? "overflow-x-auto " : "") +
        className
      }
    >
      {children}
    </div>
  );
}
