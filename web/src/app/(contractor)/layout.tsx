import { redirect } from "next/navigation";
import type { ReactNode } from "react";

import { viewerFor } from "@/common/auth/guard";
import { ForbiddenPage } from "@/common/layout/forbidden-page";

// Signed-in, never cached (ADR 0003). The contractor shell comes in W1b.
export const dynamic = "force-dynamic";

export default async function ContractorLayout({ children }: { children: ReactNode }) {
  const viewer = await viewerFor(["contractor"]);
  if (viewer.status === "signed_out") redirect("/sign-in");
  if (viewer.status === "forbidden") return <ForbiddenPage portal="contractor" me={viewer.me} />;
  return children;
}
