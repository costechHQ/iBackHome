"use client";

import { useQueryClient } from "@tanstack/react-query";
import { WifiOff } from "lucide-react";
import { createContext, useContext, useMemo, useState, useSyncExternalStore, type ReactNode } from "react";

import { formatClock } from "../time";

// Online state for the whole app. The web queues nothing: while offline every write button is hidden or
// disabled (common/actions.ts takes `online`), and the offline bar says so (WEB-CLIENT-024 "Offline").

function subscribe(onChange: () => void) {
  window.addEventListener("online", onChange);
  window.addEventListener("offline", onChange);
  return () => {
    window.removeEventListener("online", onChange);
    window.removeEventListener("offline", onChange);
  };
}

export function useOnline(): boolean {
  return useSyncExternalStore(
    subscribe,
    () => navigator.onLine,
    () => true,
  );
}

const TimeZoneContext = createContext("Africa/Lagos");

/** The viewer's time zone (clients: their own; Nigerian roles: WAT), set once by the portal layout. */
export function ViewerTimeZone({ timeZone, children }: { timeZone: string; children: ReactNode }) {
  return <TimeZoneContext.Provider value={timeZone}>{children}</TimeZoneContext.Provider>;
}

export function useViewerTimeZone(): string {
  return useContext(TimeZoneContext);
}

/** The time data last loaded: the newest successful query, or when the page loaded. */
function useLastLoaded(online: boolean): string {
  const client = useQueryClient();
  const [pageLoaded] = useState(() => new Date().toISOString());
  // Worked out again each time the connection drops, when the bar appears.
  return useMemo(() => {
    if (online) return pageLoaded;
    const newest = Math.max(
      0,
      ...client
        .getQueryCache()
        .getAll()
        .map((q) => q.state.dataUpdatedAt),
    );
    return newest ? new Date(newest).toISOString() : pageLoaded;
  }, [online, client, pageLoaded]);
}

/** `force` shows it while online (dev gallery only). */
export function OfflineBar({ force = false }: { force?: boolean }) {
  const online = useOnline() && !force;
  const timeZone = useViewerTimeZone();
  const lastLoaded = useLastLoaded(online);
  if (online) return null;
  return (
    <div
      role="status"
      className="ibh-on-navy type-small flex items-center gap-3 bg-navy-900 px-4 py-2.5 font-semibold text-white sm:px-8"
    >
      <WifiOff aria-hidden strokeWidth={1.75} className="size-5 flex-none" />
      <p>
        You&apos;re offline. Showing what loaded at {formatClock(lastLoaded, timeZone)}. Approvals and
        payments are paused until you&apos;re back.
      </p>
    </div>
  );
}
