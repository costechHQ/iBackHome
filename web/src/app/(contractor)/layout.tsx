import { redirect } from "next/navigation";
import type { ReactNode } from "react";

import { viewerFor } from "@/common/auth/guard";
import { contactOf } from "@/common/auth/contact";
import { ContractorTop } from "@/common/layout/contractor-shell";
import { ForbiddenPage } from "@/common/layout/forbidden-page";
import { OfflineBar } from "@/common/layout/online";
import { PortalProviders } from "@/common/layout/portal-providers";
import { mockFlags } from "@/common/layout/shell-data";
import { viewerTimeZone } from "@/common/time";
import { onboardingFor } from "@/features/auth/onboarding/server";
import { SessionExpiredDialog } from "@/features/auth/session-expired";

// Signed-in, never cached (ADR 0004).
export const dynamic = "force-dynamic";

export default async function ContractorLayout({ children }: { children: ReactNode }) {
  const viewer = await viewerFor(["contractor"]);
  if (viewer.status === "signed_out") redirect("/sign-in");
  if (viewer.status === "forbidden") return <ForbiddenPage portal="contractor" me={viewer.me} />;
  // Consent and the required profile steps come first (W5b).
  if ((await onboardingFor(viewer.me)).length) redirect("/welcome");
  return (
    <PortalProviders
      viewer={{
        id: viewer.me.id,
        role: "contractor",
        fullName: viewer.me.full_name,
        contact: contactOf(viewer.me),
      }}
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
