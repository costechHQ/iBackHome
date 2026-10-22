import { redirect } from "next/navigation";
import type { ReactNode } from "react";

import { viewerFor } from "@/common/auth/guard";
import { ForbiddenPage } from "@/common/layout/forbidden-page";

// Signed-in, never cached (ADR 0003). The ops shell comes in W1b.
export const dynamic = "force-dynamic";

export default async function OpsLayout({ children }: { children: ReactNode }) {
  const viewer = await viewerFor(["ops"]);
  if (viewer.status === "signed_out") redirect("/sign-in");
  if (viewer.status === "forbidden") return <ForbiddenPage portal="ops" me={viewer.me} />;
  return children;
}
