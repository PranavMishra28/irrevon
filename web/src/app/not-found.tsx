import { Link, useLocation } from "@tanstack/react-router";
import { Page } from "@/shared/ui/layout/page";

/**
 * Not-found state: preserves the entered path/id, offers the palette and
 * Effects, and never guesses that an unknown id might be an orphan.
 */
export function NotFound() {
  const location = useLocation();

  return (
    <Page
      title="No exact match"
      lead="Nothing is addressed by this path. Detent routes on exact identifiers only — it does not guess."
    >
      <div className="max-w-2xl rounded-(--radius-structural) border border-border bg-layer-panel p-5">
        <dl className="grid grid-cols-[max-content_1fr] gap-x-4 gap-y-1.5 text-sm">
          <dt className="text-text-tertiary">Requested</dt>
          <dd className="font-mono text-xs break-all text-text-primary">{location.pathname}</dd>
        </dl>
        <p className="mt-3 text-sm text-text-secondary">
          Use the command palette (<kbd className="font-mono text-xs">⌘K</kbd>) with an exact
          64-hex effect id or typed id, or return to the ledger.
        </p>
        <Link
          to="/effects"
          className={
            "mt-4 inline-flex h-8 items-center rounded-(--radius-control) border border-border " +
            "bg-layer-panel px-3 text-sm font-medium text-text-primary hover:bg-(--sys-state-hover)"
          }
        >
          Go to Effects
        </Link>
      </div>
    </Page>
  );
}
