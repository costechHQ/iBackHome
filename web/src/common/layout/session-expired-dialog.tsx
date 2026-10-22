"use client";

import * as AlertPrimitive from "@radix-ui/react-alert-dialog";
import { useEffect, useState } from "react";

import { SESSION_EXPIRED_EVENT } from "../api/client";
import { Button } from "../ui/button";

// WEB-CLIENT-024 "Session expired": shown when the API proxy says the session has ended (it already tried one
// refresh). It can't be dismissed: the only way on is signing in, which brings the person back to this page.
// The design's "[12 hours]" is a placeholder and is left out (the backend decides when sessions end).

/** `forceOpen` shows it without a 401 (dev gallery only). */
export function SessionExpiredDialog({ forceOpen = false }: { forceOpen?: boolean }) {
  const [open, setOpen] = useState(forceOpen);
  useEffect(() => {
    const show = () => setOpen(true);
    window.addEventListener(SESSION_EXPIRED_EVENT, show);
    return () => window.removeEventListener(SESSION_EXPIRED_EVENT, show);
  }, []);

  const signIn = () => {
    const here = `${window.location.pathname}${window.location.search}`;
    // A full page load: the person signing back in may be someone else, so no cached data survives.
    // eslint-disable-next-line @next/next/no-location-assign-relative-destination
    window.location.assign(`/sign-in?next=${encodeURIComponent(here)}&expired=1`);
  };

  return (
    <AlertPrimitive.Root open={open}>
      <AlertPrimitive.Portal>
        <AlertPrimitive.Overlay className="fixed inset-0 z-40 bg-ink/50" />
        <AlertPrimitive.Content
          onEscapeKeyDown={(e) => e.preventDefault()}
          className="fixed inset-x-4 top-1/2 z-50 mx-auto flex max-w-md -translate-y-1/2 flex-col gap-3 rounded-dialog bg-white p-6 shadow-dialog"
        >
          <AlertPrimitive.Title className="type-h3 text-ink">Please sign in again</AlertPrimitive.Title>
          <AlertPrimitive.Description className="text-slate">
            For your security, you were signed out. Sign in and we&apos;ll bring you back to this page.
            Nothing you started was approved or paid.
          </AlertPrimitive.Description>
          <AlertPrimitive.Action asChild>
            <Button size="lg" block onClick={signIn} className="mt-2">
              Sign in
            </Button>
          </AlertPrimitive.Action>
        </AlertPrimitive.Content>
      </AlertPrimitive.Portal>
    </AlertPrimitive.Root>
  );
}
