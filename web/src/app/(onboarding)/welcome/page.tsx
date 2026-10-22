import type { Metadata } from "next";
import { redirect } from "next/navigation";

import { viewerFor } from "@/common/auth/guard";
import { homeFor } from "@/common/auth/roles";
import { SignOutButton } from "@/common/auth/sign-out-button";
import { Wordmark } from "@/common/ui/wordmark";
import { Onboarding } from "@/features/auth/onboarding/onboarding";
import { onboardingFor } from "@/features/auth/onboarding/server";

export const metadata: Metadata = { title: "Welcome · iBackHome" };

// Signed-in, never cached (ADR 0004).
export const dynamic = "force-dynamic";

// WEB-CLIENT-001, WEB-CONTRACTOR-002 and the consent card. The portal layouts send people here while a step
// is missing; when nothing is, it goes on to their portal.
export default async function WelcomePage() {
  const viewer = await viewerFor(["client", "contractor"]);
  if (viewer.status === "signed_out") redirect("/sign-in?next=%2Fwelcome");
  if (viewer.status === "forbidden") redirect("/home");
  const { me } = viewer;
  const home = homeFor(me.role) ?? "/home";
  const missing = await onboardingFor(me);
  if (!missing.length) redirect(home);
  return (
    <div className="flex min-h-dvh flex-col bg-canvas">
      <header className="flex items-center justify-between border-b border-line bg-white px-4 py-3 sm:px-8">
        <Wordmark />
        <SignOutButton className="type-small rounded-control font-semibold text-ink underline" />
      </header>
      <main className="flex flex-1 flex-col px-4 py-8 sm:py-10">
        <Onboarding
          me={{
            role: me.role as "client" | "contractor",
            full_name: me.full_name,
            phone: me.phone,
            email: me.email,
            country: me.country,
            timezone: me.timezone,
          }}
          missing={missing}
          home={home}
        />
      </main>
    </div>
  );
}
