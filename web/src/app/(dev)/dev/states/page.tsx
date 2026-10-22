import { notFound } from "next/navigation";

import { StatesGallery } from "@/common/dev/states-gallery";
import { SessionExpiredDialog } from "@/features/auth/session-expired";

// Development only: 404 unless IBH_DEV_PAGES=1 (never set in Docker, staging or production).
export const dynamic = "force-dynamic";

export default async function StatesPage({ searchParams }: { searchParams: Promise<{ frame?: string }> }) {
  if (process.env.IBH_DEV_PAGES !== "1") notFound();
  const { frame } = await searchParams;
  return (
    <StatesGallery frame={frame ?? null} slots={{ sessionExpired: <SessionExpiredDialog forceOpen /> }} />
  );
}
