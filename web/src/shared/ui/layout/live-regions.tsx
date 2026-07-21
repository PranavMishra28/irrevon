import { createContext, useCallback, useContext, useMemo, useRef, useState } from "react";
import type { ReactNode } from "react";

/**
 * Two permanent live regions: polite status and assertive alert.
 * Assertive is reserved for connection loss or demo artifact failure —
 * never routine polling updates.
 */

interface Announcer {
  announce: (message: string) => void;
  alert: (message: string) => void;
}

const AnnouncerContext = createContext<Announcer | null>(null);

export function useAnnouncer(): Announcer {
  const ctx = useContext(AnnouncerContext);
  if (!ctx) throw new Error("useAnnouncer must be used inside <LiveRegionProvider>");
  return ctx;
}

export function LiveRegionProvider({ children }: { children: ReactNode }) {
  const [status, setStatus] = useState("");
  const [alertText, setAlertText] = useState("");
  const clearTimer = useRef<ReturnType<typeof setTimeout> | undefined>(undefined);

  const announce = useCallback((message: string) => {
    setStatus("");
    // Re-set in the next frame so repeat announcements are re-spoken.
    requestAnimationFrame(() => {
      setStatus(message);
    });
    clearTimeout(clearTimer.current);
    clearTimer.current = setTimeout(() => {
      setStatus("");
    }, 5000);
  }, []);

  const alert = useCallback((message: string) => {
    setAlertText("");
    requestAnimationFrame(() => {
      setAlertText(message);
    });
  }, []);

  const value = useMemo(() => ({ announce, alert }), [announce, alert]);

  return (
    <AnnouncerContext.Provider value={value}>
      {children}
      <div role="status" aria-live="polite" className="sr-only">
        {status}
      </div>
      <div role="alert" aria-live="assertive" className="sr-only">
        {alertText}
      </div>
    </AnnouncerContext.Provider>
  );
}
