/**
 * Icon registry — the only module allowed to import lucide-react.
 * Curated re-exports keep the icon language single-weight and reviewable.
 * Sizes 12/14/16/20 only; icons inherit currentColor; meaning-bearing icons
 * always pair with a text label at the call site.
 */
export {
  ArrowUpRight,
  Ban,
  Check,
  CheckSquare,
  ChevronDown,
  ChevronRight,
  Circle,
  CircleCheck,
  CircleDashed,
  Clock,
  Copy,
  Eye,
  EyeOff,
  FileX,
  HelpCircle,
  Menu,
  Moon,
  RotateCw,
  Search,
  Sun,
  Undo2,
  Unlink,
  User,
  X,
} from "lucide-react";

// Domain glyphs — original in-house geometry on the same grid (see domain.tsx).
export {
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
  Persist,
  Probe,
  Recovery,
  SeatSettle,
  StableId,
} from "./domain";

/**
 * Custom domain glyph on Lucide's grid rules (24px, 2px stroke, round caps):
 * a destination sheet separated from the ledger — the ORPHANED finding scene.
 */
export function OrphanSheet({ size = 14 }: { size?: number }) {
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
      {/* ledger spine, left */}
      <path d="M5 4v16" />
      <path d="M5 6h3M5 12h3M5 18h3" />
      {/* separated sheet, right, offset from the ledger */}
      <path d="M13 5h5a1 1 0 0 1 1 1v12a1 1 0 0 1-1 1h-5a1 1 0 0 1-1-1V6a1 1 0 0 1 1-1Z" />
      <path d="M15.5 11.2a1.3 1.3 0 1 1 1.8 1.2c-.5.2-.8.5-.8 1" />
      <path d="M16.5 15.8h.01" />
    </svg>
  );
}
