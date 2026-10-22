import Link from "next/link";

import { homeFor } from "../auth/roles";
import { SignOutButton } from "../auth/sign-out-button";
import { Button, buttonVariants } from "../ui/button";
import { ERROR_ICONS, ErrorPage } from "./error-page";

const PORTAL_NAMES: Record<string, string> = {
  client: "the client",
  contractor: "contractors",
  ops: "the iBackHome team",
};

// WEB-CLIENT-024 "Permission denied · 403": who you are signed in as, and the way to your own pages.
export function ForbiddenPage({
  portal,
  me,
}: {
  portal: string;
  me: { full_name: string | null; role: string; status: string };
}) {
  const home = homeFor(me.role);
  const name = me.full_name ?? "this account";
  const suspended = me.status !== "active";
  return (
    <main className="flex min-h-dvh flex-col">
      <ErrorPage
        icon={ERROR_ICONS.forbidden}
        title={
          suspended ? "This account is suspended" : `This page is only for ${PORTAL_NAMES[portal] ?? portal}`
        }
        code="Error 403"
        actions={
          <>
            {home && !suspended ? (
              <Button asChild size="lg">
                <Link href={home}>Go to my projects</Link>
              </Button>
            ) : null}
            <SignOutButton className={buttonVariants({ variant: "outline", size: "lg" })} />
          </>
        }
      >
        {suspended ? (
          <p>Contact us if you think this is a mistake. Nothing in your projects was changed.</p>
        ) : (
          <p>
            You&apos;re signed in as {name} ({me.role}).
            {me.role === "supervisor" ? " Supervisors use the iBackHome Android app." : ""}
            {me.role === "supplier" ? " The supplier portal isn't open yet." : ""}
          </p>
        )}
      </ErrorPage>
    </main>
  );
}
