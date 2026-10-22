import { redirect } from "next/navigation";
import type { ReactNode } from "react";

import { viewerFor } from "@/common/auth/guard";
import { contactOf } from "@/common/auth/contact";
import { ClientMain, ClientNav, ClientTop } from "@/common/layout/client-shell";
import { ForbiddenPage } from "@/common/layout/forbidden-page";
import { OfflineBar } from "@/common/layout/online";
import { PortalProviders } from "@/common/layout/portal-providers";
import { mockFlags, clientProjects } from "@/common/layout/shell-data";
import { viewerTimeZone } from "@/common/time";
import { onboardingFor } from "@/features/auth/onboarding/server";
import { SessionExpiredDialog } from "@/features/auth/session-expired";

// Signed-in, never cached (ADR 0004).
export const dynamic = "force-dynamic";

export default async function ClientLayout({ children }: { children: ReactNode }) {
  const viewer = await viewerFor(["client"]);
  if (viewer.status === "signed_out") redirect("/sign-in");
  if (viewer.status === "forbidden") return <ForbiddenPage portal="client" me={viewer.me} />;
  // Consent and the required profile steps come first (W5b).
  if ((await onboardingFor(viewer.me)).length) redirect("/welcome");
  const projects = await clientProjects();
  return (
    <PortalProviders
      viewer={{
        id: viewer.me.id,
        role: "client",
        fullName: viewer.me.full_name,
        contact: contactOf(viewer.me),
      }}
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
