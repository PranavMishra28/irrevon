import { useNavigate } from "@tanstack/react-router";
import { useEffect, useRef, useState } from "react";
import type { KeyboardEvent, ReactNode } from "react";
import type { ReconciliationFinding } from "@/shared/contracts/generated/reconciliation-finding";
import { FindingBadge } from "@/shared/domain/status/finding-badge";
import { ResolutionTag } from "@/shared/domain/status/resolution-tag";
import { truncateEffectId, truncateTypedId } from "@/shared/lib/ids";
import { getSingleKeyShortcutsEnabled } from "@/shared/lib/prefs";
import { RecordCard } from "@/shared/ui/primitives/record-card";
import { InspectionSeatBar } from "@/shared/ui/primitives/inspection-frame";
import { FindingInspector } from "./inspector";

/**
 * Findings projections (REDESIGN-BRIEF §5.5): a complete table at ≥1120
 * with a docked 440px inspector; a two-column card grid at 768–1119 with an
 * inline inspector below the selected card; one-column cards below 768.
 * Selection is URL-backed (`selected`); j/k move, Enter inspects, `o` opens
 * the owning effect only when one exists, Escape closes and restores focus.
 */

const COLUMNS = ["Finding", "Subject", "Classification", "Resolution", "Evidence", "Created"];

function classificationCell(finding: ReconciliationFinding): ReactNode {
  return finding.classification === "DUPLICATE" && finding.excess_effect_count !== undefined ? (
    <FindingBadge value="DUPLICATE" excessEffectCount={finding.excess_effect_count} />
  ) : (
    <FindingBadge value={finding.classification} />
  );
}

function subjectCell(finding: ReconciliationFinding): ReactNode {
  if ("effect_id" in finding.subject) {
    return (
      <span className="machine-id font-mono text-xs text-text-primary">
        {truncateEffectId(finding.subject.effect_id)}
      </span>
    );
  }
  return (
    <span className="machine-id font-mono text-xs break-all text-text-secondary">
      {finding.subject.adapter_id} · {finding.subject.destination_ref}
      <span className="ml-1.5 text-2xs text-text-tertiary">
        (destination-keyed — no ledger record)
      </span>
    </span>
  );
}

export function FindingsList({
  findings,
  selectedId,
  onSelect,
}: {
  findings: ReconciliationFinding[];
  selectedId: string | null;
  onSelect: (findingId: string | null) => void;
}) {
  const navigate = useNavigate();
  const [focusIndex, setFocusIndex] = useState(0);
  const containerRef = useRef<HTMLDivElement>(null);

  const selected = findings.find((f) => f.finding_id === selectedId) ?? null;

  // Keep roving focus valid when the set changes.
  useEffect(() => {
    setFocusIndex((index) => Math.min(index, Math.max(0, findings.length - 1)));
  }, [findings.length]);

  const focusRow = (index: number) => {
    const next = Math.max(0, Math.min(findings.length - 1, index));
    setFocusIndex(next);
    requestAnimationFrame(() => {
      containerRef.current?.querySelector<HTMLElement>(`[data-finding-row="${next}"]`)?.focus();
    });
  };

  const openOwningEffect = (finding: ReconciliationFinding) => {
    if ("effect_id" in finding.subject) {
      void navigate({
        to: "/effects/$effectId",
        params: { effectId: finding.subject.effect_id },
      });
    }
  };

  const onKeyDown = (event: KeyboardEvent<HTMLElement>) => {
    const singleKeys = getSingleKeyShortcutsEnabled();
    const finding = findings[focusIndex];
    if (event.key === "ArrowDown" || (singleKeys && event.key === "j")) {
      event.preventDefault();
      focusRow(focusIndex + 1);
    } else if (event.key === "ArrowUp" || (singleKeys && event.key === "k")) {
      event.preventDefault();
      focusRow(focusIndex - 1);
    } else if (event.key === "Home") {
      event.preventDefault();
      focusRow(0);
    } else if (event.key === "End") {
      event.preventDefault();
      focusRow(findings.length - 1);
    } else if (event.key === "Enter" && finding) {
      event.preventDefault();
      onSelect(finding.finding_id);
    } else if (singleKeys && event.key === "o" && finding) {
      event.preventDefault();
      openOwningEffect(finding);
    } else if (event.key === "Escape" && selected) {
      event.preventDefault();
      onSelect(null);
      focusRow(focusIndex);
    }
  };

  const inspector = selected ? (
    <FindingInspector
      finding={selected}
      onClose={() => {
        onSelect(null);
        focusRow(focusIndex);
      }}
    />
  ) : null;

  return (
    <div ref={containerRef} className="min-w-0">
      {/* ≥1120: full table + docked inspector */}
      <div className="hidden gap-4 min-[1120px]:flex">
        <div
          className={
            "min-w-0 flex-1 rounded-(--radius-structural) border border-border " +
            "bg-layer-workspace"
          }
        >
          <table className="w-full border-collapse text-sm" aria-label="Findings">
            <thead>
              <tr>
                {COLUMNS.map((column) => (
                  <th
                    key={column}
                    scope="col"
                    className={
                      "border-b border-border px-(--dt-cell-pad-x) py-2 text-left font-mono " +
                      "text-2xs font-medium tracking-wide text-text-tertiary uppercase"
                    }
                  >
                    {column}
                  </th>
                ))}
              </tr>
            </thead>
            <tbody>
              {findings.map((finding, index) => {
                const isSelected = finding.finding_id === selectedId;
                return (
                  <tr
                    key={finding.finding_id}
                    data-finding-row={index}
                    tabIndex={index === focusIndex ? 0 : -1}
                    onKeyDown={onKeyDown}
                    data-selected={isSelected || undefined}
                    onFocus={() => {
                      setFocusIndex(index);
                    }}
                    onClick={() => {
                      onSelect(finding.finding_id);
                    }}
                    className={
                      "h-(--dt-row-h) border-b border-border-subtle last:border-b-0 " +
                      "hover:bg-(--sys-state-hover) " +
                      "focus:outline-2 focus:-outline-offset-2 focus:outline-(--color-border-focus) " +
                      (isSelected ? "relative bg-layer-panel" : "")
                    }
                  >
                    <td className="relative px-(--dt-cell-pad-x) py-1 font-mono text-xs">
                      {isSelected ? <InspectionSeatBar /> : null}
                      {truncateTypedId(finding.finding_id)}
                    </td>
                    <td className="px-(--dt-cell-pad-x) py-1">{subjectCell(finding)}</td>
                    <td className="px-(--dt-cell-pad-x) py-1">{classificationCell(finding)}</td>
                    <td className="px-(--dt-cell-pad-x) py-1">
                      <ResolutionTag value={String(finding.resolution.status)} />
                    </td>
                    <td className="px-(--dt-cell-pad-x) py-1 font-mono text-2xs text-text-tertiary">
                      {finding.evidence_digest.slice(0, 15)}…{finding.evidence_digest.slice(-4)}{" "}
                      ({finding.evidence.redaction})
                    </td>
                    <td className="px-(--dt-cell-pad-x) py-1 font-mono text-2xs text-text-tertiary">
                      <time dateTime={finding.created_at}>
                        {finding.created_at.slice(0, 19).replace("T", " ")}Z
                      </time>
                    </td>
                  </tr>
                );
              })}
            </tbody>
          </table>
        </div>
        {inspector ? <div className="w-[440px] shrink-0">{inspector}</div> : null}
      </div>

      {/* <1120: card grid; the inspector renders inline after the selected card */}
      <ul className="grid grid-cols-1 gap-3 min-[768px]:grid-cols-2 min-[1120px]:hidden">
        {findings.map((finding, index) => {
          const isSelected = finding.finding_id === selectedId;
          return (
            <li key={finding.finding_id} className="min-w-0">
              <button
                type="button"
                data-finding-row={`card-${index}`}
                onKeyDown={onKeyDown}
                aria-expanded={isSelected}
                onClick={() => {
                  onSelect(isSelected ? null : finding.finding_id);
                }}
                className="w-full text-left"
              >
                <RecordCard
                  heading={truncateTypedId(finding.finding_id)}
                  meta={finding.created_by}
                  inspected={isSelected}
                  fields={[
                    {
                      label: "Subject",
                      value: subjectCell(finding),
                    },
                    {
                      label: "Evidence",
                      value: `${finding.evidence_digest.slice(0, 15)}… (${finding.evidence.redaction})`,
                    },
                    {
                      label: "Created",
                      value: (
                        <time dateTime={finding.created_at}>
                          {finding.created_at.slice(0, 19).replace("T", " ")}Z
                        </time>
                      ),
                    },
                  ]}
                  statuses={
                    <dl className="grid grid-cols-[max-content_1fr] items-center gap-x-3 gap-y-1">
                      <dt className="font-mono text-2xs tracking-wide text-text-tertiary uppercase">
                        Classification
                      </dt>
                      <dd>{classificationCell(finding)}</dd>
                      <dt className="font-mono text-2xs tracking-wide text-text-tertiary uppercase">
                        Resolution
                      </dt>
                      <dd>
                        <ResolutionTag value={String(finding.resolution.status)} />
                      </dd>
                    </dl>
                  }
                />
              </button>
              {isSelected ? (
                <div className="mt-2 min-[768px]:col-span-2">{inspector}</div>
              ) : null}
            </li>
          );
        })}
      </ul>
    </div>
  );
}
