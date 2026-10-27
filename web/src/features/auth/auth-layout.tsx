import { Camera, Check, ChevronLeft, CircleCheck, Lock } from "lucide-react";
import Image from "next/image";
import Link from "next/link";
import type { ReactNode } from "react";

import { Button } from "@/common/ui/button";
import { Wordmark } from "@/common/ui/wordmark";

// The frames around the sign-in card: the public split screen (WEB-PUBLIC-010), the ops card on navy
// (WEB-OPS-001) and the signed-out page. Privacy, Terms and Help links wait for their pages (PACKAGE-REPORT W-2).

const PROMISES = [
  { icon: Camera, text: "Evidence captured on your site and checked before you see it" },
  { icon: Lock, text: "Money held by a licensed escrow partner" },
  { icon: CircleCheck, text: "Released only when the supervisor verifies and you approve" },
];

export function PublicAuthFrame({ children }: { children: ReactNode }) {
  return (
    <div className="grid min-h-dvh bg-white lg:grid-cols-5">
      <aside className="ibh-on-navy relative isolate hidden flex-col justify-between overflow-hidden bg-navy-900 p-12 text-white lg:col-span-2 lg:flex">
        {/* A silent, looping video as the backdrop, faded so the words on top stay easy to read. The still of a
            home shows while it loads, and instead of the video for visitors who ask for less motion. */}
        <Image
          aria-hidden
          src="/landing/abuja-modern-home.jpg"
          alt=""
          width={900}
          height={1350}
          priority
          sizes="40vw"
          className="absolute inset-0 -z-10 hidden size-full object-cover opacity-15 motion-reduce:block"
        />
        <video
          aria-hidden
          autoPlay
          muted
          loop
          playsInline
          poster="/landing/abuja-modern-home.jpg"
          className="absolute inset-0 -z-10 size-full object-cover opacity-15 motion-reduce:hidden"
        >
          <source src="/landing/sign-in-bg.mp4" type="video/mp4" />
        </video>
        <Wordmark onDark size="lg" className="self-start" />
        <div className="flex flex-col gap-8">
          <p className="type-display">Far from home, never out of sight.</p>
          <ul className="flex flex-col gap-4">
            {PROMISES.map(({ icon: Icon, text }) => (
              <li key={text} className="flex items-start gap-3 text-navy-200">
                <Icon aria-hidden strokeWidth={1.75} className="mt-0.5 size-5 flex-none" />
                <span>{text}</span>
              </li>
            ))}
          </ul>
        </div>
        <p className="type-small text-navy-200">
          Client funds are held by a licensed escrow partner, never by iBackHome.
        </p>
      </aside>
      <div className="flex flex-col lg:col-span-3">
        <header className="flex items-center justify-between border-b border-line px-4 py-3 lg:border-0 lg:px-12 lg:py-8">
          <span className="lg:invisible">
            <Wordmark />
          </span>
          <Link
            href="/"
            className="type-small hidden items-center gap-1 rounded-control font-semibold text-ink lg:flex"
          >
            <ChevronLeft aria-hidden strokeWidth={2} className="size-4" />
            Back to the website
          </Link>
        </header>
        <main className="flex flex-1 justify-center px-4 py-6 lg:items-start lg:px-12 lg:py-4">
          <div className="w-full max-w-md lg:rounded-card lg:border lg:border-line lg:p-9 lg:shadow-card">
            {children}
          </div>
        </main>
        <p className="type-small px-4 pb-6 text-muted lg:hidden">
          Client funds are held by a licensed escrow partner, never by iBackHome.
        </p>
      </div>
    </div>
  );
}

export function OpsAuthFrame({ children }: { children: ReactNode }) {
  return (
    <main className="flex min-h-dvh items-center justify-center bg-navy-900 px-4 py-10">
      <div className="flex w-full max-w-lg flex-col gap-6 rounded-dialog bg-white p-9 shadow-dialog">
        <div className="flex items-center gap-2">
          <Wordmark />
          <span className="type-caption rounded-tag bg-mist px-1.5 text-slate">Operations</span>
        </div>
        {children}
      </div>
    </main>
  );
}

export function SignedOut() {
  return (
    <div className="flex min-h-dvh flex-col bg-canvas">
      <header className="border-b border-line bg-white px-4 py-3 sm:px-8">
        <Wordmark />
      </header>
      <main className="flex flex-1 items-center justify-center px-4 py-10">
        <div className="flex w-full max-w-xl flex-col items-center gap-4 rounded-card border border-line bg-white p-10 text-center shadow-card">
          <span className="flex size-14 items-center justify-center rounded-pill bg-ok-bg text-ok-fg">
            <Check aria-hidden strokeWidth={2} className="size-6" />
          </span>
          <h1 className="type-h2 text-ink">You&apos;ve signed out</h1>
          <p className="text-slate">
            You&apos;re signed out on this browser. If you used a shared computer, close the window too.
          </p>
          <Button asChild size="lg" block>
            <Link href="/sign-in">Sign in again</Link>
          </Button>
          <Link href="/" className="rounded-control font-semibold text-accent underline">
            Back to the website
          </Link>
        </div>
      </main>
    </div>
  );
}
