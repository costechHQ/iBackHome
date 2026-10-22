"use client";

import { useState } from "react";

import { signOutHere } from "./leave";

/** Ends the session on this browser and shows the signed-out page. */
export function SignOutButton({ className }: { className?: string }) {
  const [busy, setBusy] = useState(false);
  return (
    <button
      type="button"
      className={className}
      disabled={busy}
      onClick={() => {
        setBusy(true);
        void signOutHere();
      }}
    >
      Sign out
    </button>
  );
}
