import { useRef, type RefObject } from "react";
import { LIFECYCLE_STATES } from "@/shared/contracts/generated/state-model";
import type { Lifecycle } from "@/shared/contracts/generated/state-model";
import type { EffectsSearch } from "@/shared/api/filters";
import { Button } from "@/shared/ui/primitives/button";

/**
 * Exact URL-backed filters (Q1 contract). Lifecycle chips toggle multi-select;
 * effect_type is an exact match. No fuzzy matching, no sort affordances —
 * ordering beyond the contract's stable cursor order is not contracted.
 */
export function EffectsFilterBar({
  search,
  onChange,
  firstControlRef,
  resultCount,
}: {
  search: EffectsSearch;
  onChange: (next: EffectsSearch) => void;
  firstControlRef: RefObject<HTMLInputElement | null>;
  resultCount: number | undefined;
}) {
  const formRef = useRef<HTMLDivElement>(null);
  const active = new Set(search.lifecycle ?? []);
  const hasFilters = (search.lifecycle?.length ?? 0) > 0 || search.effect_type !== undefined;

  const toggleLifecycle = (value: Lifecycle) => {
    const next = new Set(active);
    if (next.has(value)) next.delete(value);
    else next.add(value);
    const lifecycle = [...next];
    const out: EffectsSearch = { ...search };
    if (lifecycle.length > 0) out.lifecycle = lifecycle;
    else delete out.lifecycle;
    delete out.cursor;
    onChange(out);
  };

  return (
    <div
      ref={formRef}
      role="search"
      aria-label="Effect filters"
      className="flex flex-wrap items-center gap-2 border-b border-border-subtle pb-3"
    >
      <label className="flex items-center gap-1.5">
        <span className="font-mono text-2xs font-medium tracking-wide text-text-tertiary uppercase">
          effect_type
        </span>
        <input
          ref={firstControlRef}
          type="text"
          defaultValue={search.effect_type ?? ""}
          placeholder="exact, e.g. order.create"
          onKeyDown={(event) => {
            if (event.key === "Enter") {
              const value = event.currentTarget.value.trim();
              const out: EffectsSearch = { ...search };
              if (value !== "") out.effect_type = value;
              else delete out.effect_type;
              delete out.cursor;
              onChange(out);
            }
          }}
          className={
            "h-7 w-56 rounded-(--radius-control) border border-border bg-surface-1 px-2 " +
            "font-mono text-xs text-text-primary placeholder:font-sans " +
            "placeholder:text-text-tertiary"
          }
        />
      </label>
      <span
        aria-hidden
        className="ml-1 font-mono text-2xs font-medium tracking-wide text-text-tertiary uppercase"
      >
        lifecycle
      </span>
      <div
        className="flex flex-wrap items-center gap-1"
        role="group"
        aria-label="Lifecycle filter"
      >
        {LIFECYCLE_STATES.map((value) => (
          <button
            key={value}
            type="button"
            aria-pressed={active.has(value)}
            onClick={() => {
              toggleLifecycle(value);
            }}
            className={
              "h-6 rounded-(--radius-control) border px-1.5 font-mono text-2xs " +
              "font-medium tracking-wide uppercase " +
              (active.has(value)
                ? "border-accent bg-accent-bg text-text-primary"
                : "border-border bg-surface-1 text-text-secondary hover:border-border-strong")
            }
          >
            {value}
          </button>
        ))}
      </div>
      {hasFilters ? (
        <Button
          variant="ghost"
          onClick={() => {
            onChange({});
          }}
        >
          Clear filters
        </Button>
      ) : null}
      <span className="ml-auto text-xs text-text-tertiary">
        {resultCount === undefined ? "" : `${resultCount} shown`}
      </span>
    </div>
  );
}
