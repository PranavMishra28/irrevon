import { Fragment, type ComponentType } from "react";
import type { Meta, StoryObj } from "@storybook/react-vite";
import {
  AdapterTierC1,
  AdapterTierC2,
  AdapterTierC3,
  Ambiguous,
  Boundary,
  Compensated,
  CrashSeam,
  DuplicateReject,
  Evidence,
  GateDeny,
  Intent,
  Ledger,
  OrphanAbsence,
  OrphanSheet,
  Persist,
  Probe,
  Recovery,
  SeatSettle,
  StableId,
} from "./index";

/**
 * Domain glyph gallery: every in-house icon at the registry's render sizes
 * plus 24px, in ink only — silhouette distinguishability is the review
 * criterion (no hue may carry the meaning).
 */
const meta = {
  title: "Icons/DomainGlyphs",
} satisfies Meta;

export default meta;
type Story = StoryObj<typeof meta>;

const GLYPHS: [string, ComponentType<{ size?: number }>][] = [
  ["ambiguous", Ambiguous],
  ["ledger", Ledger],
  ["boundary", Boundary],
  ["recovery", Recovery],
  ["probe", Probe],
  ["orphan-absence", OrphanAbsence],
  ["evidence", Evidence],
  ["adapter-tier C1", AdapterTierC1],
  ["adapter-tier C2", AdapterTierC2],
  ["adapter-tier C3", AdapterTierC3],
  ["compensated", Compensated],
  ["persist", Persist],
  ["crash-seam", CrashSeam],
  ["seat-settle", SeatSettle],
  ["stable-id", StableId],
  ["gate-deny", GateDeny],
  ["intent", Intent],
  ["duplicate-reject", DuplicateReject],
  ["orphan-sheet (kept)", OrphanSheet],
];

export const Gallery: Story = {
  render: () => (
    <div className="grid grid-cols-[max-content_repeat(4,max-content)] items-center gap-x-6 gap-y-2 text-text-primary">
      <span className="font-mono text-2xs text-text-tertiary">glyph</span>
      {[12, 16, 20, 24].map((size) => (
        <span key={size} className="font-mono text-2xs text-text-tertiary">
          {size}px
        </span>
      ))}
      {GLYPHS.map(([name, Icon]) => (
        <Fragment key={name}>
          <span className="font-mono text-xs text-text-secondary">{name}</span>
          {[12, 16, 20, 24].map((size) => (
            <span key={size} className="flex items-center">
              <Icon size={size} />
            </span>
          ))}
        </Fragment>
      ))}
    </div>
  ),
};
