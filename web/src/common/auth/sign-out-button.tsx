"use client";

import { useState } from "react";

/** Ends the session on this browser (clears the cookies) and goes to sign-in. */
export function SignOutButton({ className }: { className?: string }) {
  const [busy, setBusy] = useState(false);
  return (
    <button
      type="button"
      className={className}
      disabled={busy}
      onClick={async () => {
        setBusy(true);
        await fetch("/api/session/sign-out", { method: "POST" }).catch(() => null);
        // A full page load, not router.push: it drops every cached query of the person who just left.
        // eslint-disable-next-line @next/next/no-location-assign-relative-destination
        window.location.assign("/sign-in");
      }}
    >
      Sign out
    </button>
  );
}
