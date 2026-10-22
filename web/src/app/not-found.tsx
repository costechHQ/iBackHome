import Link from "next/link";

import { NotFoundContent } from "@/common/layout/system-pages";
import { Wordmark } from "@/common/ui/wordmark";

// A URL nothing matches. The portal shells have their own not-found pages for notFound() inside a portal.
export default function NotFound() {
  return (
    <div className="flex min-h-dvh flex-col">
      <header className="border-b border-line bg-white">
        <div className="mx-auto flex h-16 max-w-7xl items-center px-4 sm:px-8">
          <Link href="/" aria-label="iBackHome home" className="rounded-control">
            <Wordmark />
          </Link>
        </div>
      </header>
      <main className="flex flex-1 flex-col">
        <NotFoundContent />
      </main>
    </div>
  );
}
