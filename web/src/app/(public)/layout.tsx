import type { ReactNode } from "react";

import { PublicFooter, PublicHeader } from "@/features/public/chrome";

// The public site (WEB-PUBLIC-001 to 009): static pages, no session needed. A signed-in visitor at "/" is sent
// to their portal by the proxy.
export default function PublicLayout({ children }: { children: ReactNode }) {
  return (
    <div className="flex min-h-dvh flex-col bg-white">
      <a
        href="#main"
        className="sr-only focus:not-sr-only focus:absolute focus:top-2 focus:left-2 focus:z-50 focus:rounded-control focus:bg-white focus:p-3"
      >
        Skip to content
      </a>
      <PublicHeader />
      <main id="main" className="flex-1">
        {children}
      </main>
      <PublicFooter />
    </div>
  );
}
