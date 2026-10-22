"use client";

import { ServerErrorContent } from "@/common/layout/system-pages";

import "./globals.css";

// When even the root layout fails: the same 500 page, with its own <html>.
export default function GlobalError({
  error,
  reset,
}: {
  error: Error & { digest?: string };
  reset: () => void;
}) {
  return (
    <html lang="en">
      <body className="flex min-h-dvh flex-col">
        <ServerErrorContent reference={error.digest ?? null} onRetry={reset} />
      </body>
    </html>
  );
}
