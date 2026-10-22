"use client";

import { createContext, useContext, type ReactNode } from "react";

import type { MockFlags, MockGap } from "./index";

const MockContext = createContext<MockFlags>([]);

/** Set once by the portal layout from IBH_MOCKS (server env). */
export function MockFlagsProvider({ flags, children }: { flags: MockFlags; children: ReactNode }) {
  return <MockContext.Provider value={flags}>{children}</MockContext.Provider>;
}

/** Is the mock for this gap switched on? When it isn't, hide what it would fill. */
export function useMock(gap: MockGap): boolean {
  return useContext(MockContext).includes(gap);
}
