import { redirect } from "next/navigation";
import type { ReactNode } from "react";

import { viewerFor } from "@/common/auth/guard";
import { ForbiddenPage } from "@/common/layout/forbidden-page";

// Signed-in, never cached (ADR 0003). The client shell comes in W1b.
export const dynamic = "force-dynamic";

export default async function ClientLayout({ children }: { children: ReactNode }) {
  const viewer = await viewerFor(["client"]);
  if (viewer.status === "signed_out") redirect("/sign-in");
  if (viewer.status === "forbidden") return <ForbiddenPage portal="client" me={viewer.me} />;
  return children;
}
