"use client";

import type { ReactNode } from "react";

import type { MockFlags } from "../api/mocks";
import { MockFlagsProvider } from "../api/mocks/context";
import { ViewerProvider, type ViewerInfo } from "../auth/viewer";
import { ViewerTimeZone } from "./online";

/** What every signed-in portal page knows: who is looking, their time zone, and which mocks are on. */
export function PortalProviders({
  viewer,
  timeZone,
  mocks,
  children,
}: {
  viewer: ViewerInfo;
  timeZone: string;
  mocks: MockFlags;
  children: ReactNode;
}) {
  return (
    <ViewerProvider viewer={viewer}>
      <ViewerTimeZone timeZone={timeZone}>
        <MockFlagsProvider flags={mocks}>{children}</MockFlagsProvider>
      </ViewerTimeZone>
    </ViewerProvider>
  );
}
