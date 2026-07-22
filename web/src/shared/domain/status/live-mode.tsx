import { SeatMark } from "@/shared/ui/layout/mark";

/**
 * Live-mode connection chrome (serve spec §3.2–§3.4). Presentational only:
 * the view state arrives from useLiveStatus() (src/app/live-status.ts), so
 * every surface here is story-testable. None of these components may name
 * a fixture value — the live-boundary sentinel scan runs over every live
 * build artifact.
 */

export type LiveStatus =
  | { state: "connecting" }
  | { state: "connected"; doctorOk: boolean; failingChecks: number; lastUpdatedAt: number }
  | { state: "disconnected"; lastUpdatedAt: number | null }
  | { state: "unsupported"; observed: string; supported: string };

function chipDotClass(status: LiveStatus): string {
  if (status.state !== "connected") return "bg-border-strong";
  return status.doctorOk ? "bg-status-green" : "bg-status-amber";
}

function chipTitle(status: LiveStatus): string {
  if (status.state === "connecting") return "Waiting for the first health probe";
  if (status.state === "connected") {
    const doctor = status.doctorOk ? "doctor ok" : `${status.failingChecks} failing check(s)`;
    return `Last refresh ${new Date(status.lastUpdatedAt).toLocaleTimeString()} · ${doctor}`;
  }
  return "Engine unreachable";
}

/**
 * Compact persistent status chip for the top bar — status, not warning, so
 * deliberately NOT the full-width banner treatment. Links to /health.
 */
export function LiveChip({ status }: { status: LiveStatus }) {
  const connected = status.state === "connected";
  return (
    <a
      href="/health"
      data-testid="live-chip"
      data-state={status.state}
      title={chipTitle(status)}
      className={
        "flex h-6 shrink-0 items-center gap-1.5 rounded-(--radius-control) border " +
        "border-border px-2 font-mono text-2xs font-medium tracking-wide uppercase " +
        "text-text-secondary hover:border-border-strong hover:text-text-primary"
      }
    >
      <span aria-hidden className={`size-1.5 rounded-full ${chipDotClass(status)}`} />
      <span aria-hidden>{connected ? "live" : "live · ?"}</span>
      <span className="sr-only">
        {connected
          ? "Live connection to the local engine — read-only, loopback only. Opens Health."
          : `Live mode, ${status.state}. Opens Health.`}
      </span>
      <span className="hidden text-text-tertiary normal-case min-[768px]:inline" aria-hidden>
        read-only · 127.0.0.1
      </span>
    </a>
  );
}

/**
 * Full-width disconnected banner — the error treatment of the banner slot.
 * Data already on screen stays visible and stale-marked; per-surface reads
 * keep failing visibly. No fixture exists in the bundle to fall back to.
 */
export function DisconnectedBanner() {
  return (
    <div
      role="alert"
      data-testid="disconnected-banner"
      className={
        "flex min-h-6 shrink-0 items-center justify-center gap-2 border-b " +
        "border-status-red bg-status-red-bg px-3 py-0.5 text-center font-mono " +
        "text-2xs font-medium tracking-wide text-status-red uppercase select-none"
      }
    >
      Engine unreachable — data may be stale. `irrevon serve` may have stopped.
    </div>
  );
}

/**
 * Blocking full-viewport refusal when the server reports a schema_version
 * this build does not support (serve spec §3.4). Rendered INSTEAD of the
 * app frame: a version-skewed evidence surface is worse than none, so no
 * route content, nav, or data may render behind it.
 */
export function VersionRefusal({
  observed,
  supported,
}: {
  observed: string;
  supported: string;
}) {
  return (
    <main
      data-testid="version-refusal"
      className="flex min-h-screen flex-col items-center justify-center gap-4 bg-canvas px-6"
    >
      <div role="alert" className="flex flex-col items-center gap-4">
        <SeatMark size={28} />
        <h1 className="text-lg font-semibold text-text-primary">
          Unsupported schema version — refusing to render
        </h1>
        <p className="max-w-md text-center text-sm text-text-secondary">
          This workbench build supports schema_version {supported}; the server reports{" "}
          {observed}. Upgrade <span className="font-mono">irrevon</span> (the workbench and
          engine ship in one package) or run the matching version.
        </p>
        <p className="font-mono text-xs text-text-tertiary">
          supported {supported} · observed {observed}
        </p>
      </div>
    </main>
  );
}
