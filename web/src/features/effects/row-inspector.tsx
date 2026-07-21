import { Link } from "@tanstack/react-router";
import { useState } from "react";
import { useEffectInspect } from "@/features/effects/queries";
import { EffectTimeline } from "@/features/effects/timeline";
import { NotFoundError } from "@/shared/api/errors";
import type { EffectListItem } from "@/shared/api/types";
import type { ResolutionStatus } from "@/shared/contracts/generated/state-model";
import { StatusTriplet } from "@/shared/domain/status/status-triplet";
import { EffectClassBadge } from "@/shared/domain/status/supporting-status";
import { useAnnouncer } from "@/shared/ui/layout/live-regions";
import { Copy, X } from "@/shared/ui/icons";
import { IconButton } from "@/shared/ui/primitives/button";
import { PanelHeader } from "@/shared/ui/primitives/panel";

/**
 * Docked single-effect inspector (REDESIGN-BRIEF A1). Exact identity, the
 * three orthogonal status channels, adapter/scope, the latest recorded
 * transition, current finding/resolution, and the door into the full causal
 * investigation. Summary and Timeline projections only — a selected row
 * never becomes a node in a fleet graph.
 */
export function EffectRowInspector({
  item,
  onClose,
}: {
  item: EffectListItem;
  onClose: () => void;
}) {
  const { announce } = useAnnouncer();
  const inspect = useEffectInspect(item.record.effect_id);
  const [projection, setProjection] = useState<"summary" | "timeline">("summary");

  const copyId = () => {
    void navigator.clipboard.writeText(item.record.effect_id).then(() => {
      announce("Effect ID copied");
    });
  };

  const latest = inspect.data
    ? [...inspect.data.timeline].sort((a, b) => b.transition_seq - a.transition_seq)[0]
    : undefined;

  return (
    <section
      aria-label={`Effect inspector ${item.record.effect_id.slice(0, 12)}`}
      data-testid="effect-row-inspector"
      className={
        "flex min-w-0 flex-col rounded-(--radius-structural) border border-border-subtle " +
        "bg-layer-panel shadow-(--sys-edge-light)"
      }
    >
      <PanelHeader
        title="Effect"
        meta={`${item.record.effect_id.slice(0, 12)}…`}
        actions={
          <>
            <IconButton label="Copy effect id" onClick={copyId}>
              <Copy size={14} />
            </IconButton>
            <IconButton label="Close inspector" onClick={onClose}>
              <X size={14} />
            </IconButton>
          </>
        }
      />
      <div
        role="tablist"
        aria-label="Inspector projections"
        className="flex border-b border-border-subtle px-2"
      >
        {(["summary", "timeline"] as const).map((p) => (
          <button
            key={p}
            type="button"
            role="tab"
            aria-selected={projection === p}
            tabIndex={projection === p ? 0 : -1}
            onClick={() => {
              setProjection(p);
            }}
            onKeyDown={(event) => {
              if (event.key === "ArrowRight" || event.key === "ArrowLeft") {
                event.preventDefault();
                setProjection(p === "summary" ? "timeline" : "summary");
              }
            }}
            className={
              "border-b-2 px-2.5 py-1.5 text-xs font-medium capitalize " +
              (projection === p
                ? "border-(--color-accent) text-text-primary"
                : "border-transparent text-text-secondary hover:text-text-primary")
            }
          >
            {p}
          </button>
        ))}
      </div>

      <div className="flex min-w-0 flex-col gap-3 p-(--dt-panel-pad)">
        {projection === "summary" ? (
          <>
            <p className="machine-id font-mono text-2xs break-all text-text-secondary">
              {item.record.effect_id}
            </p>
            <dl className="grid grid-cols-[max-content_1fr] items-baseline gap-x-3 gap-y-1.5">
              <dt className="font-mono text-2xs tracking-wide text-text-tertiary uppercase">
                Type
              </dt>
              <dd className="font-mono text-xs text-text-primary">{item.record.effect_type}</dd>
              <dt className="font-mono text-2xs tracking-wide text-text-tertiary uppercase">
                Class
              </dt>
              <dd>
                <EffectClassBadge value={item.record.effect_class} />
              </dd>
              <dt className="font-mono text-2xs tracking-wide text-text-tertiary uppercase">
                Scope
              </dt>
              <dd className="font-mono text-xs text-text-primary">{item.record.scope}</dd>
              <dt className="font-mono text-2xs tracking-wide text-text-tertiary uppercase">
                Adapter
              </dt>
              <dd className="font-mono text-xs text-text-primary">{item.record.adapter_id}</dd>
            </dl>
            <div className="border-t border-border-subtle pt-2">
              <StatusTriplet
                lifecycle={item.record.lifecycle}
                classification={item.classification}
                resolution={
                  item.finding
                    ? (String(item.finding.resolution.status) as ResolutionStatus)
                    : undefined
                }
                excessEffectCount={item.finding?.excess_effect_count ?? undefined}
              />
            </div>
            {latest ? (
              <div className="border-t border-border-subtle pt-2">
                <h4 className="font-mono text-2xs font-medium tracking-wide text-text-tertiary uppercase">
                  Latest recorded transition
                </h4>
                <p className="mt-1 font-mono text-xs break-words text-text-primary">
                  {latest.from_state ?? "∅"} → {latest.to_state}
                  <span className="text-text-tertiary"> · cause {latest.cause}</span>
                </p>
                <p className="machine-id font-mono text-2xs text-text-tertiary">
                  <time dateTime={latest.created_at}>{latest.created_at}</time>
                </p>
              </div>
            ) : inspect.isError && inspect.error instanceof NotFoundError ? (
              <p className="text-sm text-text-secondary">No inspect payload for this id.</p>
            ) : null}
          </>
        ) : inspect.data ? (
          <EffectTimeline payload={inspect.data} />
        ) : inspect.isError ? (
          <p className="font-mono text-xs text-text-secondary">{inspect.error.message}</p>
        ) : (
          <div className="min-h-24" aria-busy="true" />
        )}

        <div className="border-t border-border-subtle pt-3">
          <Link
            to="/effects/$effectId"
            params={{ effectId: item.record.effect_id }}
            className={
              "inline-flex h-8 items-center rounded-(--radius-control) border border-accent " +
              "bg-accent px-3 text-sm font-medium text-text-inverse hover:bg-accent-hover"
            }
          >
            Open causal investigation
          </Link>
        </div>
      </div>
    </section>
  );
}
