"use client";

import { ServerErrorContent } from "@/common/layout/system-pages";

// An unexpected error inside this portal: the 500 page inside the portal's own shell.
export default function Error({ error, reset }: { error: Error & { digest?: string }; reset: () => void }) {
  return <ServerErrorContent reference={error.digest ?? null} onRetry={reset} />;
}
