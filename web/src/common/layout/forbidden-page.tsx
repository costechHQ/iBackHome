import Link from "next/link";

import { homeFor } from "../auth/roles";
import { SignOutButton } from "../auth/sign-out-button";

const PORTAL_NAMES: Record<string, string> = {
  client: "the client",
  contractor: "contractors",
  ops: "the iBackHome team",
};

// Copy from WEB-CLIENT-024 "Permission denied · 403". W1a version: plain layout; W1b gives it the designed
// error-page look.
export function ForbiddenPage({
  portal,
  me,
}: {
  portal: string;
  me: { full_name: string | null; role: string; status: string };
}) {
  const home = homeFor(me.role);
  const name = me.full_name ?? "this account";
  return (
    <main className="mx-auto flex max-w-xl flex-col gap-4 px-4 py-16">
      <h1 className="type-h2 text-ink">This page is only for {PORTAL_NAMES[portal] ?? portal}</h1>
      {me.status !== "active" ? (
        <p>This account is suspended. Contact us if you think this is a mistake.</p>
      ) : (
        <p>
          You&apos;re signed in as {name} ({me.role}).{" "}
          {me.role === "supervisor" && "Supervisors use the iBackHome Android app."}
          {me.role === "supplier" && "The supplier portal isn't open yet."}
        </p>
      )}
      <div className="flex flex-wrap gap-3">
        {home && me.status === "active" && (
          <Link className="text-accent underline hover:text-accent-hover" href={home}>
            Go to my projects
          </Link>
        )}
        <SignOutButton className="text-accent underline hover:text-accent-hover" />
      </div>
      <p className="type-small text-muted">Error 403</p>
    </main>
  );
}
