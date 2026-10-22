"use client";

import * as AlertPrimitive from "@radix-ui/react-alert-dialog";
import { useQueryClient } from "@tanstack/react-query";
import { useEffect, useState } from "react";

import { SESSION_EXPIRED_EVENT } from "@/common/api/client";
import { signOutHere } from "@/common/auth/leave";
import { useOptionalViewer } from "@/common/auth/viewer";
import { Button } from "@/common/ui/button";

import { CodeStep, ProblemAlert } from "./auth-card";
import { maskIdentifier } from "./otp";
import { useOtp } from "./use-otp";

// "Please sign in again" (WEB-CLIENT-002 on phones as a bottom sheet, WEB-OPS-001 frame 3 on desktop), shown
// when the API proxy says the session has ended (it already tried one refresh). The code goes to the same
// person (their email, else their phone) and is entered here, so they stay on the page and nothing on it is
// lost. It can't be dismissed: "Not now" signs out. Without a known contact (the dev gallery) "Send me a code"
// opens the sign-in page, which brings them back.

/** `forceOpen` shows it without a 401 (dev gallery only). */
export function SessionExpiredDialog({ forceOpen = false }: { forceOpen?: boolean }) {
  const [open, setOpen] = useState(forceOpen);
  const contact = useOptionalViewer()?.contact ?? null;
  const queries = useQueryClient();
  const otp = useOtp(() => {
    setOpen(false);
    // Everything the page shows is fetched again under the new session.
    void queries.invalidateQueries();
  });

  const { restart } = otp;
  useEffect(() => {
    const show = () => {
      // A fresh start each time the session ends (a code from an earlier time is no use).
      restart();
      setOpen(true);
    };
    window.addEventListener(SESSION_EXPIRED_EVENT, show);
    return () => window.removeEventListener(SESSION_EXPIRED_EVENT, show);
  }, [restart]);

  const sendCode = () => {
    if (contact) {
      otp.send(contact.identifier, contact.channel);
      return;
    }
    const here = `${window.location.pathname}${window.location.search}`;
    // eslint-disable-next-line @next/next/no-location-assign-relative-destination
    window.location.assign(`/sign-in?next=${encodeURIComponent(here)}&expired=1`);
  };

  return (
    <AlertPrimitive.Root open={open}>
      <AlertPrimitive.Portal>
        <AlertPrimitive.Overlay className="fixed inset-0 z-40 bg-ink/50" />
        <AlertPrimitive.Content
          onEscapeKeyDown={(e) => e.preventDefault()}
          className="fixed inset-x-0 bottom-0 z-50 flex max-h-dvh flex-col gap-4 overflow-y-auto rounded-t-dialog bg-white p-5 pb-6 shadow-dialog sm:inset-x-4 sm:top-1/2 sm:bottom-auto sm:mx-auto sm:max-w-md sm:-translate-y-1/2 sm:rounded-dialog sm:p-6"
        >
          <span aria-hidden className="mx-auto h-1 w-10 rounded-pill bg-line-strong sm:hidden" />
          {otp.sent ? (
            <>
              <AlertPrimitive.Description className="sr-only">
                Enter the 6-digit code to carry on where you were.
              </AlertPrimitive.Description>
              <CodeStep
                otp={otp}
                fixed
                heading={(text) => (
                  <AlertPrimitive.Title className="type-h3 text-ink">{text}</AlertPrimitive.Title>
                )}
              />
            </>
          ) : (
            <>
              <AlertPrimitive.Title className="type-h3 text-ink">Please sign in again</AlertPrimitive.Title>
              <AlertPrimitive.Description className="text-slate">
                Your session ended for your security. Nothing has changed on your project, and we&apos;ll keep
                you on this page.
                {contact ? ` We'll send a code to ${maskIdentifier(contact.identifier)}.` : ""}
              </AlertPrimitive.Description>
              <ProblemAlert otp={otp} />
              <div className="flex flex-col gap-3 sm:flex-row-reverse">
                <Button size="lg" block loading={otp.requesting} onClick={sendCode}>
                  Send me a code
                </Button>
                <Button size="lg" block variant="outline" onClick={() => void signOutHere()}>
                  Not now
                </Button>
              </div>
            </>
          )}
        </AlertPrimitive.Content>
      </AlertPrimitive.Portal>
    </AlertPrimitive.Root>
  );
}
