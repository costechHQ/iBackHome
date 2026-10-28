"use client";

import { ArrowUpRight, Menu, X } from "lucide-react";
import Link from "next/link";
import { usePathname } from "next/navigation";
import { useState } from "react";

import { Button } from "@/common/ui/button";
import { cn } from "@/common/ui/cn";
import { Wordmark } from "@/common/ui/wordmark";

import { FooterOrbit } from "./footer-orbit";
import { FooterSocials } from "./footer-socials";
import { Reveal } from "./reveal";
import { copyrightLine, SITE } from "./site";

// The public site's header and footer (WEB-PUBLIC-001 to 009). One call to action everywhere: "Get started",
// which is sign-in (a new person signs up there). On phones the links fold into a menu.

export const PUBLIC_NAV = [
  { label: "How it works", href: "/how-it-works" },
  { label: "Pricing", href: "/pricing" },
  { label: "For contractors", href: "/contractors" },
  { label: "Become a supervisor", href: "/supervisors" },
  { label: "Trust and safety", href: "/trust" },
  { label: "Contact", href: "/contact" },
] as const;

export function PublicHeader() {
  const pathname = usePathname();
  const [open, setOpen] = useState(false);
  return (
    <header className="sticky top-0 z-30 border-b border-line bg-white">
      <div className="mx-auto flex h-16 max-w-336 items-center gap-6 px-4 sm:px-8 lg:px-12 xl:px-16">
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
    <footer className="ibh-on-navy relative isolate overflow-hidden bg-navy-900 text-navy-200">
      <div aria-hidden className="absolute inset-0 -z-10">
        <div className="ibh-float absolute -top-32 -left-24 size-112 rounded-full bg-accent/20 blur-3xl" />
        <div className="ibh-float absolute -right-24 bottom-0 size-96 rounded-full bg-navy-700 blur-3xl [--ibh-delay:2s]" />
      </div>

      <div className="mx-auto flex max-w-336 flex-col gap-14 px-4 pt-12 pb-8 sm:px-8 lg:px-12 lg:pt-16 xl:px-16">
        <Reveal>
          <div className="rounded-3xl grid items-center gap-8 overflow-hidden bg-white p-8 shadow-raised lg:grid-cols-2 lg:p-12">
            <div className="flex flex-col items-start gap-4">
              <p className="type-caption text-muted uppercase">Talk to us</p>
              <h2 className="type-h1 text-ink">Questions about your build?</h2>
              <p className="type-body-lg text-slate">
                Ask about a build, joining as a contractor or supervisor, or partnering with us.
              </p>
              <Button asChild size="lg">
                <Link href="/contact">
                  Contact us
                  <ArrowUpRight aria-hidden strokeWidth={1.75} className="size-4" />
                </Link>
              </Button>
            </div>
            <FooterOrbit />
          </div>
        </Reveal>

        <div className="grid gap-10 lg:grid-cols-5">
          <Reveal className="flex flex-col gap-3 lg:col-span-2">
            <Wordmark onDark size="lg" className="self-start" />
            <p className="text-white">Far from home, never out of sight.</p>
            <p className="type-small max-w-sm">
              Client funds are held by a licensed escrow partner, never by iBackHome.
            </p>
          </Reveal>
          {FOOTER.map((col, i) => (
            <Reveal key={col.heading} delay={(i + 1) * 100}>
              <nav aria-label={col.heading} className="flex flex-col gap-3">
                <p className="type-caption text-x-on-navy-muted uppercase">{col.heading}</p>
                <ul className="flex flex-col gap-2">
                  {col.links.map((l) => (
                    <li key={l.href}>
                      <Link
                        href={l.href}
                        className="group inline-flex items-center gap-1 rounded-control text-white"
                      >
                        <span className="group-hover:underline">{l.label}</span>
                        <ArrowUpRight
                          aria-hidden
                          strokeWidth={1.75}
                          className="size-3.5 text-navy-200 transition-transform duration-300 group-hover:translate-x-0.5 group-hover:-translate-y-0.5"
                        />
                      </Link>
                    </li>
                  ))}
                </ul>
              </nav>
            </Reveal>
          ))}
        </div>

        <div className="type-small flex flex-wrap items-center justify-between gap-4 border-t border-navy-700 pt-6">
          <div className="flex flex-wrap items-center gap-x-6 gap-y-3">
            <FooterSocials />
            <p>{copyrightLine()}</p>
          </div>
          {address ? <p>{address}</p> : null}
        </div>
      </div>
    </footer>
  );
}
