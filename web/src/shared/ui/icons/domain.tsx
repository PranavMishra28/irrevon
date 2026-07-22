import type { ReactNode } from "react";

/**
 * Domain glyphs — original hand-written geometry (N4, 2026-07-21), adopted
 * per the rebuild identity brief. Lucide's published grid conventions
 * (24px viewBox, 2px stroke, round caps/joins, currentColor) are followed
 * for pixel coherence beside the remaining Lucide picks at 12/14/16/20px;
 * no Lucide path is reused, traced, or modified. Every glyph pairs with a
 * text label at meaning-bearing call sites (registry rule, kept).
 */

interface IconProps {
  // `| undefined` so wrappers can forward their own optional size under
  // exactOptionalPropertyTypes.
  size?: number | undefined;
}

function Glyph({ size = 14, children }: IconProps & { children: ReactNode }) {
  return (
    <svg
      xmlns="http://www.w3.org/2000/svg"
      viewBox="0 0 24 24"
      width={size}
      height={size}
      fill="none"
      stroke="currentColor"
      strokeWidth="2"
      strokeLinecap="round"
      strokeLinejoin="round"
      aria-hidden="true"
    >
      {children}
    </svg>
  );
}

/**
 * ambiguous — the taxonomy's dashed grammar as a frame: a dashed slot
 * holding a question. Destination state unknown is a rendered object, never
 * blank — and distinct from the chrome help-circle.
 */
export function Ambiguous({ size }: IconProps) {
  return (
    <Glyph size={size}>
      <rect x="3" y="3" width="18" height="18" rx="2" strokeDasharray="3 3" />
      <path d="M9.6 9.2a2.4 2.4 0 1 1 3.7 2c-.8.55-1.3 1-1.3 1.9" />
      <path d="M12 17h.01" />
    </Glyph>
  );
}

/**
 * ledger — ruled append-only rows closed by the accountant's double rule
 * beneath the last entry: totals are struck, never rewritten. Replaces the
 * "Database" cylinder, which claims storage, not bookkeeping.
 */
export function Ledger({ size }: IconProps) {
  return (
    <Glyph size={size}>
      <path d="M4 5h16" />
      <path d="M4 9.5h16" />
      <path d="M4 14h10" />
      <path d="M4 18.5h16" />
      <path d="M4 21.5h16" />
    </Glyph>
  );
}

/**
 * boundary — the irreversible dispatch boundary: dashed track before, solid
 * track after, and the armed pawl wedge angled against the reverse
 * direction. Matches the graph's notch annotation; replaces "Lock", which
 * promises access security the product does not make.
 */
export function Boundary({ size }: IconProps) {
  return (
    <Glyph size={size}>
      <path d="M12 3v18" />
      <path d="M3 12h5" strokeDasharray="2.5 2.5" />
      <path d="M16 12h5" />
      <path d="M13 4.5h4.5L15 8.3z" fill="currentColor" stroke="none" />
    </Glyph>
  );
}

/**
 * recovery — a three-quarter replay arc that terminates on the double rule:
 * recovery replays the ledger and adjudicates; it is NOT a circular retry
 * loop — the arc lands, once, on the books.
 */
export function Recovery({ size }: IconProps) {
  return (
    <Glyph size={size}>
      <path d="M18.5 13.5A6.5 6.5 0 1 1 12 7h4.5" />
      <path d="m14 4.5 2.5 2.5L14 9.5" />
      <path d="M4 20.5h16" />
    </Glyph>
  );
}

/**
 * probe (read-back) — a query line reaching down to touch a hatched
 * destination stratum and nothing more: reconcile-by-query reads, it never
 * writes.
 */
export function Probe({ size }: IconProps) {
  return (
    <Glyph size={size}>
      <path d="M12 3v9.5" />
      <path d="M12 12.5l2.8-2.8" />
      <path d="M4 17h16" />
      <path d="M6 20.5h2M11 20.5h2M16 20.5h2" />
    </Glyph>
  );
}

/**
 * orphan-absence — a solid destination observation beside a dashed void
 * slot: something exists at the destination with no ledger record to pair
 * it with. Absence is drawn, never left blank.
 */
export function OrphanAbsence({ size }: IconProps) {
  return (
    <Glyph size={size}>
      <rect x="3" y="6" width="7.5" height="12" rx="1.5" />
      <path d="M6.75 10v4" />
      <rect x="13.5" y="6" width="7.5" height="12" rx="1.5" strokeDasharray="2.6 2.6" />
    </Glyph>
  );
}

/**
 * evidence — a record sheet with one cited line and a return corner-arrow:
 * evidence flows back across the boundary; the effect it describes stays
 * seated.
 */
export function Evidence({ size }: IconProps) {
  return (
    <Glyph size={size}>
      <rect x="5" y="3" width="14" height="18" rx="2" />
      <path d="M9 8h6" />
      <path d="M15 15.5h-4.5" />
      <path d="m12.5 13.5-2 2 2 2" />
    </Glyph>
  );
}

/**
 * adapter-tier — three capability cells, filled per tier: what the
 * destination exposes decides what any method can guarantee. One glyph
 * family makes the tier ordinal (replaces three unrelated metaphors).
 */
function AdapterTier({ size, cells }: IconProps & { cells: 1 | 2 | 3 }) {
  return (
    <Glyph size={size}>
      {[3, 9.5, 16].map((x, i) =>
        i < cells ? (
          <rect
            key={x}
            x={x}
            y="8"
            width="5"
            height="8"
            rx="1"
            fill="currentColor"
            stroke="none"
          />
        ) : (
          <rect key={x} x={x} y="8" width="5" height="8" rx="1" />
        ),
      )}
    </Glyph>
  );
}

export function AdapterTierC1({ size }: IconProps) {
  return <AdapterTier size={size} cells={3} />;
}

export function AdapterTierC2({ size }: IconProps) {
  return <AdapterTier size={size} cells={2} />;
}

export function AdapterTierC3({ size }: IconProps) {
  return <AdapterTier size={size} cells={1} />;
}

/**
 * compensated — the counter-entry. ADR-007: compensation is not rollback —
 * a compensating action is a NEW forward effect recorded against the first,
 * so the drawing is two same-direction entries landing on the accountant's
 * double rule: the original inscription and, later and beside it, the
 * counter-entry that opposes it ON THE BOOKS. Deliberately not a bent-back
 * arrow (`Undo2` retired): nothing that crossed the boundary comes back.
 * Original geometry in the persist idiom (17th glyph, designed here per
 * N4's grid rules; flagged for the owner's review in the PR body).
 */
export function Compensated({ size }: IconProps) {
  return (
    <Glyph size={size}>
      <path d="M8 3v8" />
      <path d="M5.2 8.2 8 11l2.8-2.8" />
      <path d="M16 5.5V11" />
      <path d="M13.2 8.2 16 11l2.8-2.8" />
      <path d="M4 15.5h16" />
      <path d="M4 19.5h16" />
    </Glyph>
  );
}

/* Micro-glyphs for the demo event list (identity brief §1.6). */

/**
 * persist — a downward inscription landing on the accountant's double rule:
 * persist-before-dispatch as bookkeeping, not "storage".
 */
export function Persist({ size }: IconProps) {
  return (
    <Glyph size={size}>
      <path d="M12 3v8" />
      <path d="M8.5 7.5 12 11l3.5-3.5" />
      <path d="M4 15.5h16" />
      <path d="M4 19.5h16" />
    </Glyph>
  );
}

/**
 * crash-seam — a horizontal record torn by a step seam (SIGKILL): the line
 * does not resume where it broke — it resumes offset, because a restart is
 * a new process reading the same ledger.
 */
export function CrashSeam({ size }: IconProps) {
  return (
    <Glyph size={size}>
      <path d="M3 10h7" />
      <path d="M14 14h7" />
      <path d="M12.5 4 10 12.5l3.5-1-2 8.5" />
    </Glyph>
  );
}

/**
 * seat-settle — the brand's ball-in-V-seat in stroke form: ball tangent to
 * both 45° walls, apex daylight kept. Held by geometry, not force.
 */
export function SeatSettle({ size }: IconProps) {
  return (
    <Glyph size={size}>
      <path d="M3 13.5h4.5l4.5 4.5 4.5-4.5H21" />
      <circle cx="12" cy="12.9" r="3.6" />
    </Glyph>
  );
}

/**
 * stable-id — three business facts of shrinking length funnel to one filled
 * point: many identifiers, one identity (SHA-256 over stable_ids).
 */
export function StableId({ size }: IconProps) {
  return (
    <Glyph size={size}>
      <path d="M4 5h16" />
      <path d="M6.5 9.5h11" />
      <path d="M9 14h6" />
      <circle cx="12" cy="19" r="1.6" fill="currentColor" stroke="none" />
    </Glyph>
  );
}

/**
 * gate-deny — the gate diamond carrying the do-not-enter bar: a DENY is an
 * evidenced outcome at the same station, not an error state.
 */
export function GateDeny({ size }: IconProps) {
  return (
    <Glyph size={size}>
      <path d="M12 2.5 21.5 12 12 21.5 2.5 12z" />
      <path d="M8.5 12h7" />
    </Glyph>
  );
}

/**
 * intent — a registered card whose arrow is poised short of the wall:
 * declared, not yet externalized.
 */
export function Intent({ size }: IconProps) {
  return (
    <Glyph size={size}>
      <rect x="3" y="5" width="18" height="14" rx="2" />
      <path d="M7 12h8" />
      <path d="M12 8.5 15.5 12 12 15.5" />
    </Glyph>
  );
}

/**
 * duplicate-reject — two offset cards collapsing to one: the front card is
 * whole, the rear duplicate is barred where it overlaps. Re-synthesis
 * collapses to one identity; the excess is refused with a citation.
 */
export function DuplicateReject({ size }: IconProps) {
  return (
    <Glyph size={size}>
      <rect x="3" y="8" width="13" height="13" rx="2" />
      <path d="M8 5V4a1.5 1.5 0 0 1 1.5-1.5H19A1.5 1.5 0 0 1 20.5 4v9.5A1.5 1.5 0 0 1 19 15" />
      <path d="M6.5 14.5h6" />
    </Glyph>
  );
}
