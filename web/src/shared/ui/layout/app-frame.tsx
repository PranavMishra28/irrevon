import type { ReactNode } from "react";
import { SeatMark } from "./mark";

/**
 * Workbench frame: skip link → banner (optional) → header (mark, nav, utilities)
 * → main. Hairline borders carry all structure; no shadows in the static plane.
 */
export function AppFrame({
  banner,
  nav,
  utilities,
  children,
}: {
  banner?: ReactNode;
  nav: ReactNode;
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
          "focus:border-border-strong focus:bg-surface-1 focus:px-3 focus:py-2 " +
          "focus:text-sm focus:text-text-primary"
        }
      >
        Skip to main content
      </a>
      {banner}
      <header className="flex h-11 shrink-0 items-center gap-4 border-b border-border bg-surface-1 px-4">
        <span className="flex items-center gap-2 text-text-primary">
          <SeatMark size={18} />
          <span className="text-sm font-semibold tracking-tight select-none">detent</span>
          <span className="mt-px text-2xs font-medium tracking-wide text-text-tertiary uppercase select-none">
            workbench
          </span>
        </span>
        <nav aria-label="Views" className="flex h-full min-w-0 flex-1 items-stretch gap-0.5">
          {nav}
        </nav>
        <div className="flex shrink-0 items-center gap-1">{utilities}</div>
      </header>
      <main id="main" className="min-w-0 flex-1">
        {children}
      </main>
    </div>
  );
}

/** Permanent disclosure banner for fixture-backed builds. */
export function DataModeBanner({ children }: { children: ReactNode }) {
  return (
    <div
      className={
        "flex h-7 shrink-0 items-center justify-center gap-2 border-b-2 border-border-strong " +
        "bg-surface-3 px-4 font-mono text-2xs font-medium tracking-wide " +
        "text-text-secondary uppercase select-none"
      }
    >
      {children}
    </div>
  );
}
