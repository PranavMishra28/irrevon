import { useNavigate } from "@tanstack/react-router";
import { useState } from "react";
import type { KeyboardEvent } from "react";
import type { EffectListItem } from "@/shared/api/types";
import { FindingBadge } from "@/shared/domain/status/finding-badge";
import { LifecyclePill } from "@/shared/domain/status/lifecycle-pill";
import { ResolutionNotApplicable, ResolutionTag } from "@/shared/domain/status/resolution-tag";
import { EffectClassBadge } from "@/shared/domain/status/supporting-status";
import { getSingleKeyShortcutsEnabled } from "@/shared/lib/prefs";
import { truncateEffectId } from "@/shared/lib/ids";
import { RecordCard } from "@/shared/ui/primitives/record-card";

/**
 * Effects record-card grid for 768–1119 (two columns) and <768 (one column).
 * Every card keeps the three explicitly labeled A/B/C status rows — never
 * one combined "status" — and no field hides behind horizontal page scroll.
 * Activation opens the full investigation (below 1120 there is no docked
 * inspector; A6 responsive data policy).
 */
export function EffectCards({ items }: { items: EffectListItem[] }) {
  const navigate = useNavigate();
  const [focusIndex, setFocusIndex] = useState(0);

  const open = (item: EffectListItem) => {
    void navigate({ to: "/effects/$effectId", params: { effectId: item.record.effect_id } });
  };

  const onKeyDown = (event: KeyboardEvent<HTMLElement>, index: number) => {
    const singleKeys = getSingleKeyShortcutsEnabled();
    const move = (next: number) => {
      event.preventDefault();
      const clamped = Math.max(0, Math.min(items.length - 1, next));
      setFocusIndex(clamped);
      document.querySelector<HTMLElement>(`[data-effect-card="${clamped}"]`)?.focus();
    };
    if (event.key === "ArrowDown" || (singleKeys && event.key === "j")) move(index + 1);
    else if (event.key === "ArrowUp" || (singleKeys && event.key === "k")) move(index - 1);
    else if (event.key === "Home") move(0);
    else if (event.key === "End") move(items.length - 1);
  };

  return (
    <ul className="grid grid-cols-1 gap-3 min-[768px]:grid-cols-2" aria-label="Effects">
      {items.map((item, index) => (
        <li key={item.record.effect_id} className="min-w-0">
          <button
            type="button"
            data-effect-card={index}
            tabIndex={index === focusIndex ? 0 : -1}
            onFocus={() => {
              setFocusIndex(index);
            }}
            onKeyDown={(event) => {
              onKeyDown(event, index);
            }}
            onClick={() => {
              open(item);
            }}
            aria-label={`Inspect effect ${truncateEffectId(item.record.effect_id)}, ${item.record.effect_type}`}
            className="w-full text-left"
          >
            <RecordCard
              heading={`${truncateEffectId(item.record.effect_id)} · ${item.record.effect_type}`}
              meta={<EffectClassBadge value={item.record.effect_class} />}
              fields={[{ label: "Scope", value: item.record.scope }]}
              statuses={
                <dl className="grid grid-cols-[max-content_1fr] items-center gap-x-3 gap-y-1">
                  <dt className="font-mono text-2xs tracking-wide text-text-tertiary uppercase">
                    Lifecycle
                  </dt>
                  <dd>
                    <LifecyclePill value={item.record.lifecycle} />
                  </dd>
                  <dt className="font-mono text-2xs tracking-wide text-text-tertiary uppercase">
                    Reconciliation
                  </dt>
                  <dd>
                    {item.finding?.classification === "DUPLICATE" &&
                    item.finding.excess_effect_count !== undefined ? (
                      <FindingBadge
                        value="DUPLICATE"
                        excessEffectCount={item.finding.excess_effect_count}
                      />
                    ) : (
                      <FindingBadge value={item.classification} />
                    )}
                  </dd>
                  <dt className="font-mono text-2xs tracking-wide text-text-tertiary uppercase">
                    Resolution
                  </dt>
                  <dd>
                    {item.finding ? (
                      <ResolutionTag value={String(item.finding.resolution.status)} />
                    ) : (
                      <ResolutionNotApplicable />
                    )}
                  </dd>
                </dl>
              }
              footer={
                <span className="text-2xs text-text-tertiary">
                  Inspect → full investigation
                </span>
              }
            />
          </button>
        </li>
      ))}
    </ul>
  );
}
