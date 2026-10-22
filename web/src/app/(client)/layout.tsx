import { redirect } from "next/navigation";
import type { ReactNode } from "react";

import { viewerFor } from "@/common/auth/guard";
import { ClientMain, ClientNav, ClientTop } from "@/common/layout/client-shell";
import { ForbiddenPage } from "@/common/layout/forbidden-page";
import { OfflineBar, ViewerTimeZone } from "@/common/layout/online";
import { SessionExpiredDialog } from "@/common/layout/session-expired-dialog";
import { clientProjects } from "@/common/layout/shell-data";
import { viewerTimeZone } from "@/common/time";

// Signed-in, never cached (ADR 0003).
export const dynamic = "force-dynamic";

export default async function ClientLayout({ children }: { children: ReactNode }) {
  const viewer = await viewerFor(["client"]);
  if (viewer.status === "signed_out") redirect("/sign-in");
  if (viewer.status === "forbidden") return <ForbiddenPage portal="client" me={viewer.me} />;
  const projects = await clientProjects();
  return (
    <ViewerTimeZone timeZone={viewerTimeZone(viewer.me)}>
      <div className="flex min-h-dvh flex-col">
        <OfflineBar />
        <ClientTop name={viewer.me.full_name ?? viewer.me.email ?? "You"} projects={projects} />
        <ClientMain>{children}</ClientMain>
        <ClientNav />
      </div>
      <SessionExpiredDialog />
    </ViewerTimeZone>
  );
}
