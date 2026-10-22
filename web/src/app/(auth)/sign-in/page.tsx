import type { Metadata } from "next";

import { safeNext } from "@/common/auth/roles";
import { SignInCard } from "@/features/auth/auth-card";
import { PublicAuthFrame } from "@/features/auth/auth-layout";

export const metadata: Metadata = { title: "Sign in · iBackHome" };

type Props = { searchParams: Promise<{ next?: string; expired?: string }> };

// WEB-PUBLIC-010
export default async function SignInPage({ searchParams }: Props) {
  const { next, expired } = await searchParams;
  return (
    <PublicAuthFrame>
      <SignInCard next={next ? safeNext(next) : null} expired={expired === "1"} />
    </PublicAuthFrame>
  );
}
