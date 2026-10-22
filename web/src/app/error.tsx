"use client";

import { ServerErrorContent } from "@/common/layout/system-pages";

// An unexpected error while rendering. The digest is the reference to quote (it is in the server log).
export default function Error({ error, reset }: { error: Error & { digest?: string }; reset: () => void }) {
  return (
    <main className="flex min-h-dvh flex-col">
      <ServerErrorContent reference={error.digest ?? null} onRetry={reset} />
    </main>
  );
}
