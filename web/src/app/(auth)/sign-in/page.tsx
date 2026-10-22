import type { Metadata } from "next";

import { safeNext } from "@/common/auth/roles";
import { SignInForm } from "@/features/auth/sign-in-form";

export const metadata: Metadata = { title: "Sign in · iBackHome" };

type Props = { searchParams: Promise<{ next?: string; expired?: string }> };

export default async function SignInPage({ searchParams }: Props) {
  const { next, expired } = await searchParams;
  return (
    <main className="mx-auto flex max-w-md flex-col gap-6 px-4 py-16">
      <div className="flex flex-col gap-2">
        <h1 className="type-h2 text-ink">Sign in or create an account</h1>
        <p>We&apos;ll send you a 6-digit code. There are no passwords.</p>
      </div>
      <SignInForm next={next ? safeNext(next) : null} expired={expired === "1"} />
      <p className="type-small text-muted">
        Client funds are held by a licensed escrow partner, never by iBackHome.
      </p>
    </main>
  );
}
