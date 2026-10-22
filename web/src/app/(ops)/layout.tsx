import { redirect } from "next/navigation";
import type { ReactNode } from "react";

import { viewerFor } from "@/common/auth/guard";
import { contactOf } from "@/common/auth/contact";
import { ForbiddenPage } from "@/common/layout/forbidden-page";
import { OfflineBar } from "@/common/layout/online";
import { PortalProviders } from "@/common/layout/portal-providers";
import { OpsSidebar } from "@/common/layout/ops-shell";
import { mockFlags, opsQueueCounts } from "@/common/layout/shell-data";
import { viewerTimeZone } from "@/common/time";
import { SessionExpiredDialog } from "@/features/auth/session-expired";

// Signed-in, never cached (ADR 0004). Desktop only (1440 design).
export const dynamic = "force-dynamic";

export default async function OpsLayout({ children }: { children: ReactNode }) {
  const viewer = await viewerFor(["ops"]);
  if (viewer.status === "signed_out") redirect("/ops/sign-in");
  if (viewer.status === "forbidden") return <ForbiddenPage portal="ops" me={viewer.me} />;
  const counts = await opsQueueCounts();
  return (
    <PortalProviders
      viewer={{
        id: viewer.me.id,
        role: "ops",
        fullName: viewer.me.full_name,
        contact: contactOf(viewer.me),
      }}
      timeZone={viewerTimeZone(viewer.me)}
      mocks={mockFlags()}
    >
      <div className="flex min-h-dvh">
        <OpsSidebar name={viewer.me.full_name ?? viewer.me.phone ?? "Ops"} counts={counts} />
        <div className="flex min-w-0 flex-1 flex-col">
          <OfflineBar />
          <main className="flex flex-1 flex-col bg-canvas">{children}</main>
        </div>
      </div>
      <SessionExpiredDialog />
    </PortalProviders>
  );
}
