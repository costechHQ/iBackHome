"use client";

import { createContext, useContext, type ReactNode } from "react";

import type { Viewer } from "../actions";
import type { Contact } from "./contact";

// Who is looking, for client components (set by the portal layout from GET /me). Decisions about what to show
// use it; the backend still checks every request.

export type ViewerInfo = Viewer & { fullName: string | null; contact?: Contact | null };

const ViewerContext = createContext<ViewerInfo | null>(null);

export function ViewerProvider({ viewer, children }: { viewer: ViewerInfo; children: ReactNode }) {
  return <ViewerContext.Provider value={viewer}>{children}</ViewerContext.Provider>;
}

/** The viewer where there may be none (the dev gallery). */
export function useOptionalViewer(): ViewerInfo | null {
  return useContext(ViewerContext);
}

export function useViewer(): ViewerInfo {
  const viewer = useContext(ViewerContext);
  if (!viewer) throw new Error("useViewer() outside a portal layout");
  return viewer;
}
