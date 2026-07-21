import type { ReactNode } from "react";
import { SeatMark } from "./mark";

/**
 * Workbench frame: skip link → banner (optional) → 48px L1 header → main
 * (L0 canvas). Hairline borders carry all structure; no shadows in the
 * static plane. Responsive contract (REDESIGN-BRIEF A6):
 *  - ≥1120px: full horizontal nav; all utilities visible.
 *  - 768–1119px: brand, active-view label, command trigger, Menu; nav and
 *    theme/density/help live in the drawer.
 *  - <768px: brand, command icon, Menu only; the active view moves into
 *    the drawer.
 * The drawer itself is composed by the root route (lazy on first use).
 */
export function AppFrame({
  banner,
  nav,
  viewLabel,
  utilities,
  children,
}: {
  banner?: ReactNode;
  nav: ReactNode;
  /** Active-view label, shown only in the 768–1119 header band. */
  viewLabel?: string;
  utilities: ReactNode;
  children: ReactNode;
}) {
  return (
    <div className="flex min-h-screen flex-col">
      <a
        href="#main"
        className={
          "sr-only focus:not-sr-only focus:fixed focus:top-2 focus:left-2 " +
          "focus:z-(--sys-z-toast) focus:rounded-(--radius-control) focus:border " +
          "focus:border-border-strong focus:bg-layer-panel focus:px-3 focus:py-2 " +
          "focus:text-sm focus:text-text-primary"
        }
      >
        Skip to main content
      </a>
      {banner}
      <header className="flex h-12 shrink-0 items-center gap-3 border-b border-border bg-layer-nav px-4">
        <span className="flex shrink-0 items-center gap-2 text-text-primary">
          <SeatMark size={18} />
          <span className="text-sm font-semibold tracking-tight select-none">irrevon</span>
          <span className="mt-px hidden text-2xs font-medium tracking-wide text-text-tertiary uppercase select-none min-[480px]:inline">
            workbench
          </span>
        </span>
        <nav
          aria-label="Views"
          className="hidden h-full min-w-0 flex-1 items-stretch gap-0.5 min-[1120px]:flex"
        >
          {nav}
        </nav>
        {/* Below 1120 the nav is in the drawer; this band carries the
            active-view label (hidden again below 768). */}
        <span className="flex min-w-0 flex-1 items-center min-[1120px]:hidden">
          {viewLabel !== undefined ? (
            <span
              data-testid="active-view-label"
              className="hidden min-w-0 truncate text-sm font-medium text-text-primary min-[768px]:inline"
            >
              {viewLabel}
            </span>
          ) : null}
        </span>
        <div className="flex shrink-0 items-center gap-1">{utilities}</div>
      </header>
      <main id="main" className="min-w-0 flex-1">
        {children}
      </main>
    </div>
  );
}

/**
 * Permanent disclosure banner for fixture-backed builds. Full width, but
 * visually quieter than any status surface (brief §5.1) — chrome ink on the
 * nav layer, single hairline; readable down to 320px.
 */
export function DataModeBanner({ children }: { children: ReactNode }) {
  return (
    <div
      className={
        "flex min-h-6 shrink-0 items-center justify-center gap-2 border-b border-border " +
        "bg-layer-nav px-3 py-0.5 text-center font-mono text-2xs font-medium " +
        "tracking-wide text-text-tertiary uppercase select-none"
      }
    >
      {children}
    </div>
  );
}
