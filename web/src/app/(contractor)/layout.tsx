import { redirect } from "next/navigation";
import type { ReactNode } from "react";

import { viewerFor } from "@/common/auth/guard";
import { ContractorTop } from "@/common/layout/contractor-shell";
import { ForbiddenPage } from "@/common/layout/forbidden-page";
import { OfflineBar } from "@/common/layout/online";
import { PortalProviders } from "@/common/layout/portal-providers";
import { SessionExpiredDialog } from "@/common/layout/session-expired-dialog";
import { mockFlags } from "@/common/layout/shell-data";
import { viewerTimeZone } from "@/common/time";

// Signed-in, never cached (ADR 0003).
export const dynamic = "force-dynamic";

export default async function ContractorLayout({ children }: { children: ReactNode }) {
  const viewer = await viewerFor(["contractor"]);
  if (viewer.status === "signed_out") redirect("/sign-in");
  if (viewer.status === "forbidden") return <ForbiddenPage portal="contractor" me={viewer.me} />;
  return (
    <PortalProviders
      viewer={{ id: viewer.me.id, role: "contractor", fullName: viewer.me.full_name }}
      timeZone={viewerTimeZone(viewer.me)}
      mocks={mockFlags()}
    >
      <div className="flex min-h-dvh flex-col">
        <OfflineBar />
        <ContractorTop name={viewer.me.full_name ?? viewer.me.phone ?? "You"} />
        <main className="flex flex-1 flex-col bg-canvas">{children}</main>
      </div>
      <SessionExpiredDialog />
    </PortalProviders>
  );
}
