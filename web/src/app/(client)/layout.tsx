import { redirect } from "next/navigation";
import type { ReactNode } from "react";

import { viewerFor } from "@/common/auth/guard";
import { ClientMain, ClientNav, ClientTop } from "@/common/layout/client-shell";
import { ForbiddenPage } from "@/common/layout/forbidden-page";
import { OfflineBar } from "@/common/layout/online";
import { PortalProviders } from "@/common/layout/portal-providers";
import { SessionExpiredDialog } from "@/common/layout/session-expired-dialog";
import { mockFlags, clientProjects } from "@/common/layout/shell-data";
import { viewerTimeZone } from "@/common/time";

// Signed-in, never cached (ADR 0003).
export const dynamic = "force-dynamic";

export default async function ClientLayout({ children }: { children: ReactNode }) {
  const viewer = await viewerFor(["client"]);
  if (viewer.status === "signed_out") redirect("/sign-in");
  if (viewer.status === "forbidden") return <ForbiddenPage portal="client" me={viewer.me} />;
  const projects = await clientProjects();
  return (
    <PortalProviders
      viewer={{ id: viewer.me.id, role: "client", fullName: viewer.me.full_name }}
      timeZone={viewerTimeZone(viewer.me)}
      mocks={mockFlags()}
    >
      <div className="flex min-h-dvh flex-col">
        <OfflineBar />
        <ClientTop name={viewer.me.full_name ?? viewer.me.email ?? "You"} projects={projects} />
        <ClientMain>{children}</ClientMain>
        <ClientNav />
      </div>
      <SessionExpiredDialog />
    </PortalProviders>
  );
}
