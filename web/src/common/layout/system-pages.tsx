import Link from "next/link";
import type { ReactNode } from "react";

import { Button } from "../ui/button";
import { ERROR_ICONS, ErrorPage } from "./error-page";

// The shared system pages (WEB-CLIENT-024), with the designed copy. "Help centre" and "Contact us" are left
// out until those pages exist (WEB-PUBLIC-007; PACKAGE-REPORT "hidden until built").

export function NotFoundContent() {
  return (
    <ErrorPage
      icon={ERROR_ICONS.notFound}
      title="We can't find that page"
      code="Error 404"
      actions={
        <Button asChild size="lg">
          <Link href="/home">Go to my projects</Link>
        </Button>
      }
    >
      <p>The link may be old, or the page was moved. Your projects and money aren&apos;t affected.</p>
    </ErrorPage>
  );
}

export function ServerErrorContent({
  reference,
  onRetry,
}: {
  reference: string | null;
  onRetry?: () => void;
}) {
  return (
    <ErrorPage
      icon={ERROR_ICONS.server}
      title="Something went wrong on our side"
      code={reference ? `Reference ${reference}` : "Error 500"}
      actions={
        onRetry ? (
          <Button size="lg" onClick={onRetry}>
            Try again
          </Button>
        ) : null
      }
    >
      <p>
        Nothing was charged, approved or released. Try again in a minute. If it keeps happening, quote the
        reference below.
      </p>
    </ErrorPage>
  );
}

/**
 * 409: something already changed (done on another device, or by someone else). Says what happened and that
 * nothing was done twice; the screen supplies the specifics and the way on ("See release status").
 */
export function ConflictState({
  title,
  children,
  actions,
  code = "Error 409",
}: {
  title: string;
  children: ReactNode;
  actions?: ReactNode;
  code?: string;
}) {
  return (
    <ErrorPage icon={ERROR_ICONS.conflict} title={title} code={code} actions={actions}>
      {children}
    </ErrorPage>
  );
}
