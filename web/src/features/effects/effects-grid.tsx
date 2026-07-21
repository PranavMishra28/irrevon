import { useNavigate } from "@tanstack/react-router";
import { useEffect, useRef, useState } from "react";
import type { KeyboardEvent, RefObject } from "react";
import { getSingleKeyShortcutsEnabled } from "@/shared/lib/prefs";
import { truncateEffectId } from "@/shared/lib/ids";
import type { EffectListItem } from "@/shared/api/types";
import { FindingBadge } from "@/shared/domain/status/finding-badge";
import { LifecyclePill } from "@/shared/domain/status/lifecycle-pill";
import { ResolutionNotApplicable, ResolutionTag } from "@/shared/domain/status/resolution-tag";
import { EffectClassBadge } from "@/shared/domain/status/supporting-status";
import { useAnnouncer } from "@/shared/ui/layout/live-regions";
import { InspectionSeatBar } from "@/shared/ui/primitives/inspection-frame";

/**
 * Native table with role="grid" and row-primary roving tabindex: exactly one
 * grid descendant is tabbable. Three separate status columns (A, B, C) —
 * never one combined "status". Keyboard: ↑/↓ (and j/k) rows, →/← cells,
 * Home/End, Ctrl+Home/End, Enter/o open, c copy id, per BRIEF §10.
 */

const COLUMNS = [
  "Effect",
  "Type",
  "Class",
  "Scope",
  "Lifecycle",
  "Reconciliation",
  "Resolution",
] as const;

export function EffectsGrid({
  items,
  filterRef,
  inspectedId = null,
  onInspect,
}: {
  items: EffectListItem[];
  filterRef: RefObject<HTMLInputElement | null>;
  /** Currently docked-inspected effect id (Detent Click seat bar on its row). */
  inspectedId?: string | null;
  /** When provided, Enter inspects in place and `o` opens the full detail. */
  onInspect?: (effectId: string | null) => void;
}) {
  const navigate = useNavigate();
  const { announce } = useAnnouncer();
  const [focusPos, setFocusPos] = useState<{ row: number; col: number | null }>({
    row: 0,
    col: null,
  });
  const tableRef = useRef<HTMLTableElement>(null);

  // Keep the roving focus target valid when the item set changes.
  useEffect(() => {
    setFocusPos((pos) => ({
      row: Math.min(pos.row, Math.max(0, items.length - 1)),
      col: pos.col,
    }));
  }, [items.length]);

  const focusCell = (row: number, col: number | null) => {
    setFocusPos({ row, col });
    requestAnimationFrame(() => {
      const selector =
        col === null ? `[data-grid-row="${row}"]` : `[data-grid-cell="${row}:${col}"]`;
      tableRef.current?.querySelector<HTMLElement>(selector)?.focus();
    });
  };

  const openRow = (row: number) => {
    const item = items[row];
    if (!item) return;
    void navigate({
      to: "/effects/$effectId",
      params: { effectId: item.record.effect_id },
    });
  };

  const copyRowId = (row: number) => {
    const item = items[row];
    if (!item) return;
    void navigator.clipboard.writeText(item.record.effect_id).then(() => {
      announce("Effect ID copied");
    });
  };

  const onKeyDown = (event: KeyboardEvent<HTMLTableElement>) => {
    const { row, col } = focusPos;
    const last = items.length - 1;
    const lastCol = COLUMNS.length - 1;
    const singleKeys = getSingleKeyShortcutsEnabled();
    const key = event.key;

    const move = (nextRow: number, nextCol: number | null) => {
      event.preventDefault();
      focusCell(Math.max(0, Math.min(last, nextRow)), nextCol);
    };

    if (key === "ArrowDown" || (singleKeys && key === "j")) move(row + 1, col);
    else if (key === "ArrowUp" || (singleKeys && key === "k")) move(row - 1, col);
    else if (key === "ArrowRight") move(row, col === null ? 0 : Math.min(lastCol, col + 1));
    else if (key === "ArrowLeft") move(row, col === null || col === 0 ? null : col - 1);
    else if (key === "Home" && event.ctrlKey) move(0, col);
    else if (key === "End" && event.ctrlKey) move(last, col);
    else if (key === "Home") move(row, col === null ? null : 0);
    else if (key === "End") move(row, col === null ? null : lastCol);
    else if (key === "PageDown") move(row + 10, col);
    else if (key === "PageUp") move(row - 10, col);
    else if (key === "Enter") {
      event.preventDefault();
      const item = items[row];
      if (onInspect && item) onInspect(item.record.effect_id);
      else openRow(row);
    } else if (singleKeys && key === "o") {
      event.preventDefault();
      openRow(row);
    } else if (key === "Escape" && onInspect && inspectedId !== null) {
      event.preventDefault();
      onInspect(null);
      focusCell(row, col);
    } else if (singleKeys && key === "c") {
      event.preventDefault();
      copyRowId(row);
    } else if (singleKeys && key === "/") {
      event.preventDefault();
      filterRef.current?.focus();
    } else if (singleKeys && key === "r") {
      event.preventDefault();
      announce("Fixture data is fixed; nothing to refresh in a review build");
    }
  };

  return (
    <table
      ref={tableRef}
      role="grid"
      aria-label="Effects"
      aria-rowcount={items.length + 1}
      className="w-full border-collapse"
      onKeyDown={onKeyDown}
    >
      <thead>
        <tr>
          {COLUMNS.map((column) => (
            <th
              key={column}
              scope="col"
              className={
                "border-b border-border px-(--dt-cell-pad-x) py-2 text-left " +
                "font-mono text-2xs font-medium tracking-wide text-text-tertiary uppercase"
              }
            >
              {column}
            </th>
          ))}
        </tr>
      </thead>
      <tbody>
        {items.map((item, rowIndex) => {
          const rowFocused = focusPos.row === rowIndex;
          const isInspected = inspectedId === item.record.effect_id;
          const cells = [
            <span key="id" className="flex items-center gap-1 font-mono text-xs">
              {isInspected ? <InspectionSeatBar /> : null}
              {truncateEffectId(item.record.effect_id)}
            </span>,
            <span key="type" className="font-mono text-xs">
              {item.record.effect_type}
            </span>,
            <EffectClassBadge key="class" value={item.record.effect_class} />,
            <span key="scope" className="font-mono text-xs text-text-secondary">
              {item.record.scope}
            </span>,
            <LifecyclePill key="lifecycle" value={item.record.lifecycle} />,
            item.finding?.classification === "DUPLICATE" &&
            item.finding.excess_effect_count !== undefined ? (
              <FindingBadge
                key="classification"
                value="DUPLICATE"
                excessEffectCount={item.finding.excess_effect_count}
              />
            ) : (
              <FindingBadge key="classification" value={item.classification} />
            ),
            item.finding ? (
              <ResolutionTag key="resolution" value={String(item.finding.resolution.status)} />
            ) : (
              <ResolutionNotApplicable key="resolution" />
            ),
          ];
          return (
            <tr
              key={item.record.effect_id}
              data-grid-row={rowIndex}
              tabIndex={rowFocused && focusPos.col === null ? 0 : -1}
              aria-rowindex={rowIndex + 2}
              aria-label={`Effect ${truncateEffectId(item.record.effect_id)}, ${item.record.effect_type}`}
              onFocus={() => {
                setFocusPos((pos) =>
                  pos.row === rowIndex ? pos : { row: rowIndex, col: null },
                );
              }}
              onClick={() => {
                if (onInspect) onInspect(item.record.effect_id);
              }}
              onDoubleClick={() => {
                openRow(rowIndex);
              }}
              className={
                "h-(--dt-row-h) border-b border-border-subtle hover:bg-(--sys-state-hover) " +
                "focus-within:bg-(--sys-state-hover) " +
                "focus:outline-2 focus:-outline-offset-2 focus:outline-(--color-border-focus) " +
                (isInspected ? "relative bg-layer-panel" : "")
              }
            >
              {cells.map((cell, colIndex) => (
                <td
                  key={COLUMNS[colIndex]}
                  role="gridcell"
                  data-grid-cell={`${rowIndex}:${colIndex}`}
                  tabIndex={rowFocused && focusPos.col === colIndex ? 0 : -1}
                  className={
                    "px-(--dt-cell-pad-x) py-1 text-sm text-text-primary " +
                    "focus:outline-2 focus:-outline-offset-2 focus:outline-(--color-border-focus)"
                  }
                >
                  {colIndex === 0 ? (
                    <a
                      href={`/effects/${item.record.effect_id}`}
                      tabIndex={-1}
                      onClick={(clickEvent) => {
                        clickEvent.preventDefault();
                        openRow(rowIndex);
                      }}
                      className="text-accent hover:underline"
                    >
                      {cell}
                    </a>
                  ) : (
                    cell
                  )}
                </td>
              ))}
            </tr>
          );
        })}
      </tbody>
    </table>
  );
}
