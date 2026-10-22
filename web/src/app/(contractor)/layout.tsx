import { redirect } from "next/navigation";
import type { ReactNode } from "react";

import { viewerFor } from "@/common/auth/guard";
import { ContractorTop } from "@/common/layout/contractor-shell";
import { ForbiddenPage } from "@/common/layout/forbidden-page";
import { OfflineBar, ViewerTimeZone } from "@/common/layout/online";
import { SessionExpiredDialog } from "@/common/layout/session-expired-dialog";
import { viewerTimeZone } from "@/common/time";

// Signed-in, never cached (ADR 0003).
export const dynamic = "force-dynamic";

export default async function ContractorLayout({ children }: { children: ReactNode }) {
  const viewer = await viewerFor(["contractor"]);
  if (viewer.status === "signed_out") redirect("/sign-in");
  if (viewer.status === "forbidden") return <ForbiddenPage portal="contractor" me={viewer.me} />;
  return (
    <ViewerTimeZone timeZone={viewerTimeZone(viewer.me)}>
      <div className="flex min-h-dvh flex-col">
        <OfflineBar />
        <ContractorTop name={viewer.me.full_name ?? viewer.me.phone ?? "You"} />
        <main className="flex flex-1 flex-col bg-canvas">{children}</main>
      </div>
      <SessionExpiredDialog />
    </ViewerTimeZone>
  );
}
