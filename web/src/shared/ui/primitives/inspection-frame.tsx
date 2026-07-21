import type { ReactNode } from "react";

/**
 * The Detent Click (REDESIGN-BRIEF §3.2): THE inspected object's machined
 * accent frame — 1.5px h-accent rectangle at the structural radius, four 6px
 * 45° corner ticks (the D1 notch walls quoted at the corners), and a 1px
 * translate-to-rest seat settle. No fill change, no shadow, no glow.
 *
 * Constraint: exactly one inspected object per workspace. Multi-selection
 * uses the selection fill, never multiple inspection frames.
 */
export function InspectionFrame({
  inspected,
  className = "",
  children,
}: {
  /** When false, renders children without the frame (stable DOM shape). */
  inspected: boolean;
  className?: string;
  children: ReactNode;
}) {
  return (
    <div className={(inspected ? "dt-inspected " : "") + "relative min-w-0 " + className}>
      {inspected ? <CornerTicks /> : null}
      {children}
    </div>
  );
}

/** The four 45° corner ticks, drawn as decorated spans in accent ink. */
export function CornerTicks() {
  return (
    <span aria-hidden className="pointer-events-none absolute inset-0">
      <span className="dt-tick dt-tick-tl" />
      <span className="dt-tick dt-tick-tr" />
      <span className="dt-tick dt-tick-bl" />
      <span className="dt-tick dt-tick-br" />
    </span>
  );
}

/**
 * Dense-row degrade: a 3px accent left seat bar plus the two left-side
 * ticks, for rows too small to carry the full frame. Place inside the
 * row's first cell (the row itself cannot host positioned children).
 */
export function InspectionSeatBar() {
  return (
    <span aria-hidden className="dt-seat-bar">
      <span className="dt-tick dt-tick-tl" />
      <span className="dt-tick dt-tick-bl" />
    </span>
  );
}
