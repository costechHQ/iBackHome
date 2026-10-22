"use client";

import { Menu, X } from "lucide-react";
import Link from "next/link";
import { usePathname } from "next/navigation";
import { useState } from "react";

import { Button } from "@/common/ui/button";
import { cn } from "@/common/ui/cn";
import { Wordmark } from "@/common/ui/wordmark";

import { copyrightLine, SITE } from "./site";

// The public site's header and footer (WEB-PUBLIC-001 to 009). One call to action everywhere: "Get started",
// which is sign-in (a new person signs up there). On phones the links fold into a menu.

export const PUBLIC_NAV = [
  { label: "How it works", href: "/how-it-works" },
  { label: "Pricing", href: "/pricing" },
  { label: "For contractors", href: "/contractors" },
  { label: "Become a supervisor", href: "/supervisors" },
  { label: "Trust and safety", href: "/trust" },
] as const;

export function PublicHeader() {
  const pathname = usePathname();
  const [open, setOpen] = useState(false);
  return (
    <header className="sticky top-0 z-30 border-b border-line bg-white">
      <div className="mx-auto flex h-16 max-w-7xl items-center gap-6 px-4 sm:px-8">
        <Link href="/" className="rounded-control" aria-label="iBackHome home">
          <Wordmark />
        </Link>
        <nav aria-label="Main" className="hidden flex-1 lg:block">
          <ul className="flex gap-1">
            {PUBLIC_NAV.map((item) => (
              <li key={item.href}>
                <Link
                  href={item.href}
                  aria-current={pathname === item.href ? "page" : undefined}
                  className={cn(
                    "type-small flex min-h-target items-center rounded-control px-3",
                    pathname === item.href ? "font-semibold text-ink" : "text-slate hover:text-ink",
                  )}
                >
                  {item.label}
                </Link>
              </li>
            ))}
          </ul>
        </nav>
        <div className="ml-auto flex items-center gap-2">
          <Link
            href="/sign-in"
            className="type-small hidden min-h-target items-center rounded-control px-3 font-semibold text-ink sm:flex"
          >
            Sign in
          </Link>
          <Button asChild>
            <Link href="/sign-in">Get started</Link>
          </Button>
          <button
            type="button"
            aria-expanded={open}
            aria-controls="public-menu"
            onClick={() => setOpen((o) => !o)}
            className="flex size-11 items-center justify-center rounded-control text-ink lg:hidden"
          >
            {open ? (
              <X aria-hidden strokeWidth={1.75} className="size-6" />
            ) : (
              <Menu aria-hidden strokeWidth={1.75} className="size-6" />
            )}
            <span className="sr-only">Menu</span>
          </button>
        </div>
      </div>
      {open ? (
        <nav id="public-menu" aria-label="Main" className="border-t border-line px-4 py-3 lg:hidden">
          <ul className="flex flex-col">
            {[...PUBLIC_NAV, { label: "Sign in", href: "/sign-in" }].map((item) => (
              <li key={item.href}>
                <Link
                  href={item.href}
                  onClick={() => setOpen(false)}
                  className="flex min-h-target items-center rounded-control px-2 text-ink"
                >
                  {item.label}
                </Link>
              </li>
            ))}
          </ul>
        </nav>
      ) : null}
    </header>
  );
}

const FOOTER = [
  { heading: "Product", links: [PUBLIC_NAV[0], PUBLIC_NAV[1], PUBLIC_NAV[4]] },
  { heading: "Join", links: [PUBLIC_NAV[2], PUBLIC_NAV[3], { label: "Sign in", href: "/sign-in" }] },
  {
    heading: "Company",
    links: [
      { label: "Contact", href: "/contact" },
      { label: "Privacy policy", href: "/privacy" },
      { label: "Terms", href: "/terms" },
    ],
  },
] as const;

export function PublicFooter() {
  const address = SITE.company.officeAddress;
  return (
    <footer className="ibh-on-navy bg-navy-900 text-navy-200">
      <div className="mx-auto grid max-w-7xl gap-10 px-4 py-12 sm:px-8 lg:grid-cols-5">
        <div className="flex flex-col gap-3 lg:col-span-2">
          <Wordmark onDark />
          <p className="text-white">Far from home, never out of sight.</p>
          <p className="type-small">
            Client funds are held by a licensed escrow partner, never by iBackHome.
          </p>
        </div>
        {FOOTER.map((col) => (
          <nav key={col.heading} aria-label={col.heading} className="flex flex-col gap-3">
            <p className="type-caption text-x-on-navy-muted uppercase">{col.heading}</p>
            <ul className="flex flex-col gap-2">
              {col.links.map((l) => (
                <li key={l.href}>
                  <Link href={l.href} className="rounded-control text-white hover:underline">
                    {l.label}
                  </Link>
                </li>
              ))}
            </ul>
          </nav>
        ))}
      </div>
      <div className="border-t border-navy-700">
        <div className="type-small mx-auto flex max-w-7xl flex-wrap justify-between gap-2 px-4 py-5 sm:px-8">
          <p>{copyrightLine()}</p>
          {address ? <p>{address}, Enugu, Nigeria</p> : null}
        </div>
      </div>
    </footer>
  );
}
