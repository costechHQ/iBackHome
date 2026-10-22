import type { Metadata } from "next";

import { safeNext } from "@/common/auth/roles";
import { SignInCard } from "@/features/auth/auth-card";
import { OpsAuthFrame } from "@/features/auth/auth-layout";

export const metadata: Metadata = { title: "Staff sign-in · iBackHome" };

type Props = { searchParams: Promise<{ next?: string; expired?: string }> };

// WEB-OPS-001 (desktop only). Outside the (ops) group: it is for signed-out staff.
export default async function OpsSignInPage({ searchParams }: Props) {
  const { next, expired } = await searchParams;
  return (
    <OpsAuthFrame>
      <SignInCard variant="ops" next={next ? safeNext(next) : null} expired={expired === "1"} />
    </OpsAuthFrame>
  );
}
