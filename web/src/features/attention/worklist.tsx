import { useNavigate } from "@tanstack/react-router";
import { useRef, useState } from "react";
import type { KeyboardEvent } from "react";
import { getSingleKeyShortcutsEnabled } from "@/shared/lib/prefs";
import { truncateEffectId, truncateTypedId } from "@/shared/lib/ids";
import type { AttentionItem } from "./derive";

/**
 * The Attention worklist: grouped by exact inclusion reason in formula
 * order, source order retained. "Grouped" never means "priority" — there is
 * no severity, rank, age threshold, SLA, owner, assignment, action, or
 * recommendation here. Every item links to its owning investigation.
 */

const GROUP_HEADINGS = [
  "Effects where lifecycle = AMBIGUOUS",
  "Findings where resolution.status IN (OPEN, ESCALATED_HUMAN)",
] as const;

export function AttentionWorklist({ items }: { items: AttentionItem[] }) {
  const navigate = useNavigate();
  const [focusIndex, setFocusIndex] = useState(0);
  const listRef = useRef<HTMLDivElement>(null);

  const focusItem = (index: number) => {
    const next = Math.max(0, Math.min(items.length - 1, index));
    setFocusIndex(next);
    requestAnimationFrame(() => {
      listRef.current?.querySelector<HTMLElement>(`[data-attention-item="${next}"]`)?.focus();
    });
  };

  const onKeyDown = (event: KeyboardEvent<HTMLAnchorElement>) => {
    const singleKeys = getSingleKeyShortcutsEnabled();
    if (event.key === "ArrowDown" || (singleKeys && event.key === "j")) {
      event.preventDefault();
      focusItem(focusIndex + 1);
    } else if (event.key === "ArrowUp" || (singleKeys && event.key === "k")) {
      event.preventDefault();
      focusItem(focusIndex - 1);
    } else if (event.key === "Home") {
      event.preventDefault();
      focusItem(0);
    } else if (event.key === "End") {
      event.preventDefault();
      focusItem(items.length - 1);
    }
  };

  const groups = [0, 1].map((group) => ({
    group,
    items: items
      .map((item, index) => ({ item, index }))
      .filter(({ item }) => item.group === group),
  }));

  return (
    <div ref={listRef} className="flex flex-col gap-4">
      {groups.map(({ group, items: groupItems }) =>
        groupItems.length > 0 ? (
          <section key={group} aria-label={GROUP_HEADINGS[group]}>
            <h3 className="border-b border-border-subtle pb-1.5 font-mono text-2xs font-medium tracking-wide text-text-tertiary uppercase">
              {GROUP_HEADINGS[group]}
            </h3>
            <ul className="mt-2 grid grid-cols-1 gap-3 min-[768px]:grid-cols-2 min-[1120px]:grid-cols-1">
              {groupItems.map(({ item, index }) => (
                <li key={item.key}>
                  <a
                    href={
                      item.target.kind === "effect"
                        ? `/effects/${item.target.effectId}`
                        : `/findings?selected=${item.target.findingId}`
                    }
                    data-attention-item={index}
                    tabIndex={index === focusIndex ? 0 : -1}
                    onKeyDown={onKeyDown}
                    onFocus={() => {
                      setFocusIndex(index);
                    }}
                    onClick={(event) => {
                      event.preventDefault();
                      if (item.target.kind === "effect") {
                        void navigate({
                          to: "/effects/$effectId",
                          params: { effectId: item.target.effectId },
                        });
                      } else {
                        void navigate({
                          to: "/findings",
                          search: { selected: item.target.findingId },
                        });
                      }
                    }}
                    aria-label={`${item.title} — ${item.reasons
                      .map((reason) => reason.detail)
                      .join("; ")}`}
                    className={
                      "flex min-h-11 flex-col gap-1 rounded-(--radius-structural) border " +
                      "border-border-subtle bg-layer-panel p-(--dt-panel-pad) " +
                      "shadow-(--sys-edge-light) hover:bg-(--sys-state-hover)"
                    }
                  >
                    <span className="flex flex-wrap items-baseline justify-between gap-x-3 gap-y-0.5">
                      <span className="machine-id font-mono text-xs font-medium text-text-primary">
                        {item.title}
                      </span>
                      <span className="machine-id font-mono text-2xs text-text-tertiary">
                        {formatKey(item.key)}
                      </span>
                    </span>
                    <span className="machine-id font-mono text-2xs break-all text-text-secondary">
                      {item.subtitle.length === 64
                        ? truncateEffectId(item.subtitle)
                        : item.subtitle}
                    </span>
                    <span className="mt-0.5 flex flex-col gap-0.5">
                      {item.reasons.map((reason) => (
                        <span
                          key={reason.detail}
                          className="font-mono text-2xs text-text-tertiary"
                        >
                          included because: {reason.detail}
                        </span>
                      ))}
                    </span>
                  </a>
                </li>
              ))}
            </ul>
          </section>
        ) : null,
      )}
    </div>
  );
}

function formatKey(key: string): string {
  const [kind, ...rest] = key.split(":");
  if (kind === "effect") {
    return `effect:${truncateEffectId(rest.join(":"))}`;
  }
  const [adapter, ...ref] = rest;
  const refJoined = ref.join(":");
  return `destination:${adapter ?? ""}:${refJoined.startsWith("fnd_") ? truncateTypedId(refJoined) : refJoined}`;
}
