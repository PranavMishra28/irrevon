import type { ReactNode } from "react";

/**
 * Route page scaffold. The h1 receives focus on full-page navigation
 * (tabindex="-1", focused by the router subscription in the root route).
 */
export function Page({
  title,
  lead,
  children,
  actions,
}: {
  title: string;
  lead?: ReactNode;
  children?: ReactNode;
  actions?: ReactNode;
}) {
  return (
    <div className="mx-auto w-full max-w-6xl px-6 py-6">
      <header className="flex items-start justify-between gap-4">
        <div>
          <h1
            tabIndex={-1}
            data-route-heading
            className="text-xl font-semibold text-text-primary"
          >
            {title}
          </h1>
          {lead ? <p className="mt-1 max-w-3xl text-sm text-text-secondary">{lead}</p> : null}
        </div>
        {actions ? <div className="shrink-0">{actions}</div> : null}
      </header>
      {children ? <div className="mt-5">{children}</div> : null}
    </div>
  );
}

/**
 * Honest placeholder state for routes whose data surface is contract-blocked.
 * States exactly what is missing and why; never renders invented data.
 */
export function ContractPendingState({
  what,
  blockedOn,
  children,
}: {
  what: string;
  blockedOn: string;
  children?: ReactNode;
}) {
  return (
    <div className="rounded-(--radius-structural) border border-border bg-layer-panel px-5 py-6">
      <p className="font-mono text-2xs font-medium tracking-wide text-text-tertiary uppercase">
        Contract pending
      </p>
      <p className="mt-2 max-w-2xl text-sm text-text-primary">{what}</p>
      <p className="mt-1.5 max-w-2xl text-sm text-text-secondary">
        Blocked on: <span className="font-mono text-xs">{blockedOn}</span>. This surface renders
        nothing until that contract exists — it does not guess.
      </p>
      {children ? <div className="mt-3">{children}</div> : null}
    </div>
  );
}
