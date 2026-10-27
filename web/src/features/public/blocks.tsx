import { Check, ChevronDown, Copy, KeyRound, Lock, MapPin, type LucideIcon } from "lucide-react";
import Image from "next/image";
import Link from "next/link";
import type { ReactNode } from "react";

import { Button } from "@/common/ui/button";
import { cn } from "@/common/ui/cn";

import { PHOTOS } from "./photos";
import { Reveal } from "./reveal";

// The six captures shown in the "every capture is checked" card; the fifth is the one highlighted.
const CAPTURE_PHOTOS = [
  { photo: PHOTOS.sandShovelling, position: "ibh-focus-50-25" },
  { photo: PHOTOS.hammeringFormwork, position: "ibh-focus-30-25" },
  { photo: PHOTOS.wheelbarrowEarth, position: "object-center" },
  { photo: PHOTOS.siteCrewScaffold, position: "ibh-focus-50-75" },
  { photo: PHOTOS.rebarCrew, position: "object-center" },
  { photo: PHOTOS.smilingCrew, position: "object-center" },
];

// Building blocks shared by the public pages: sections, eyebrows, feature cards, the FAQ (native details, so it
// works without JavaScript), the closing call to action, and the two product illustrations. The illustrations
// use neutral wording only: the designs' sample names and amounts aren't published (PACKAGE-REPORT W-37).

export function Section({
  tone = "white",
  className,
  children,
  labelledBy,
}: {
  tone?: "white" | "mist" | "navy";
  className?: string;
  children: ReactNode;
  labelledBy?: string;
}) {
  return (
    <section
      aria-labelledby={labelledBy}
      className={cn(
        tone === "mist" && "bg-canvas",
        tone === "navy" && "ibh-on-navy bg-navy-900 text-navy-200",
        tone === "white" && "bg-white",
      )}
    >
      <div
        className={cn(
          "mx-auto flex max-w-336 flex-col gap-8 px-4 py-14 sm:px-8 lg:px-12 lg:py-20 xl:px-16",
          className,
        )}
      >
        {children}
      </div>
    </section>
  );
}

export function Eyebrow({ children, onDark }: { children: ReactNode; onDark?: boolean }) {
  return (
    <p className={cn("type-caption uppercase", onDark ? "text-x-on-navy-muted" : "text-muted")}>{children}</p>
  );
}

export function SectionHead({
  id,
  eyebrow,
  title,
  lead,
  onDark,
  action,
  centered,
}: {
  id: string;
  eyebrow?: string;
  title: string;
  lead?: ReactNode;
  onDark?: boolean;
  action?: ReactNode;
  /** Centre the eyebrow, title and lead instead of aligning them to the left. */
  centered?: boolean;
}) {
  return (
    <div className={cn("flex flex-wrap items-end gap-4", centered ? "justify-center" : "justify-between")}>
      <div className={cn("flex max-w-3xl flex-col gap-3", centered && "items-center text-center")}>
        {eyebrow ? <Eyebrow onDark={onDark}>{eyebrow}</Eyebrow> : null}
        <h2 id={id} className={cn("type-h1", onDark ? "text-white" : "text-ink")}>
          {title}
        </h2>
        {lead ? <p className={cn("type-body-lg", onDark ? "text-navy-200" : "text-slate")}>{lead}</p> : null}
      </div>
      {action}
    </div>
  );
}

/** A grid item that, when `animate` is set, fades and lifts in as it scrolls into view, one after another. */
function GridItem({
  animate,
  index,
  className,
  children,
}: {
  animate?: boolean;
  index: number;
  className: string;
  children: ReactNode;
}) {
  if (!animate) return <li className={className}>{children}</li>;
  return (
    <li className="flex">
      <Reveal delay={index * 120} className="flex w-full">
        <div className={cn(className, "w-full transition-transform duration-300 hover:-translate-y-1")}>
          {children}
        </div>
      </Reveal>
    </li>
  );
}

export function FeatureCards({
  items,
  columns = 3,
  onDark,
  animate,
}: {
  items: readonly { icon?: LucideIcon; title: string; body: ReactNode }[];
  columns?: 1 | 2 | 3 | 4;
  onDark?: boolean;
  animate?: boolean;
}) {
  return (
    <ul
      className={cn(
        "grid gap-4",
        columns === 1 && "grid-cols-1",
        columns === 2 && "sm:grid-cols-2",
        columns === 3 && "sm:grid-cols-2 lg:grid-cols-3",
        columns === 4 && "sm:grid-cols-2 lg:grid-cols-4",
      )}
    >
      {items.map(({ icon: Icon, title, body }, i) => (
        <GridItem
          key={title}
          animate={animate}
          index={i}
          className={cn(
            "flex flex-col gap-2 rounded-card border p-5",
            onDark ? "border-navy-700 bg-navy-800" : "border-line bg-white shadow-card",
          )}
        >
          {Icon ? (
            <span
              className={cn(
                "flex size-10 items-center justify-center rounded-control",
                onDark ? "bg-navy-700 text-white" : "bg-mist text-navy-900",
              )}
            >
              <Icon aria-hidden strokeWidth={1.75} className="size-5" />
            </span>
          ) : null}
          <h3 className={cn("type-h3", onDark ? "text-white" : "text-ink")}>{title}</h3>
          <p className={onDark ? "text-navy-200" : "text-slate"}>{body}</p>
        </GridItem>
      ))}
    </ul>
  );
}

export function Steps({
  items,
  animate,
  columns = 4,
}: {
  items: readonly { title: string; body: ReactNode; tag?: string }[];
  animate?: boolean;
  /** Four across on large screens by default; 2 for a narrower column. */
  columns?: 2 | 4;
}) {
  return (
    <ol className={cn("grid gap-4 sm:grid-cols-2", columns === 4 && "lg:grid-cols-4")}>
      {items.map((s, i) => (
        <GridItem
          key={s.title}
          animate={animate}
          index={i}
          className="flex flex-col gap-2 rounded-card border border-line bg-white p-5 shadow-card"
        >
          <span className="flex items-center gap-2">
            <span className="type-small flex size-8 items-center justify-center rounded-pill bg-navy-900 font-semibold text-white">
              {i + 1}
            </span>
            {s.tag ? <span className="type-caption text-muted uppercase">{s.tag}</span> : null}
          </span>
          <h3 className="type-h3 text-ink">{s.title}</h3>
          <p className="text-slate">{s.body}</p>
        </GridItem>
      ))}
    </ol>
  );
}

export function CheckList({ items }: { items: readonly ReactNode[] }) {
  return (
    <ul className="flex flex-col gap-2">
      {items.map((item, i) => (
        <li key={i} className="flex items-start gap-3 text-ink">
          <Check aria-hidden strokeWidth={2} className="mt-1 size-4 flex-none text-ok-fg" />
          <span>{item}</span>
        </li>
      ))}
    </ul>
  );
}

export function Faq({ items }: { items: readonly { q: string; a: ReactNode }[] }) {
  return (
    <div className="flex flex-col divide-y divide-line rounded-card border border-line bg-white">
      {items.map(({ q, a }) => (
        <details key={q} className="group px-5 py-4">
          <summary className="flex cursor-pointer list-none items-center justify-between gap-4 rounded-control font-semibold text-ink">
            {q}
            <ChevronDown
              aria-hidden
              strokeWidth={1.75}
              className="size-5 flex-none text-slate group-open:rotate-180"
            />
          </summary>
          <div className="mt-3 text-slate">{a}</div>
        </details>
      ))}
    </div>
  );
}

export function CtaBand({
  title,
  lead,
  secondary,
}: {
  title: string;
  lead?: string;
  secondary?: { label: string; href: string };
}) {
  return (
    <section aria-labelledby="cta" className="bg-white">
      <div className="mx-auto max-w-336 px-4 py-14 sm:px-8 lg:px-12 lg:py-20 xl:px-16">
        <div className="flex flex-col items-center gap-4 rounded-card bg-canvas px-6 py-12 text-center">
          <h2 id="cta" className="type-h1 max-w-2xl text-ink">
            {title}
          </h2>
          {lead ? <p className="type-body-lg max-w-xl text-slate">{lead}</p> : null}
          <div className="flex flex-wrap justify-center gap-3">
            <Button asChild size="lg">
              <Link href="/sign-in">Get started</Link>
            </Button>
            {secondary ? (
              <Button asChild size="lg" variant="outline">
                <Link href={secondary.href}>{secondary.label}</Link>
              </Button>
            ) : null}
          </div>
        </div>
      </div>
    </section>
  );
}

export function PageHero({
  eyebrow,
  title,
  lead,
  children,
}: {
  eyebrow: string;
  title: string;
  lead: ReactNode;
  children?: ReactNode;
}) {
  return (
    <section className="bg-white">
      <div className="mx-auto flex max-w-336 flex-col gap-4 px-4 pt-14 pb-10 sm:px-8 lg:px-12 lg:pt-20 xl:px-16">
        <Eyebrow>{eyebrow}</Eyebrow>
        <h1 className="type-display max-w-4xl text-ink">{title}</h1>
        <p className="type-body-lg max-w-3xl text-slate">{lead}</p>
        {children}
      </div>
    </section>
  );
}

const CHECKS = [
  { icon: MapPin, label: "Inside the site boundary" },
  { icon: KeyRound, label: "Signed by a registered phone" },
  { icon: Copy, label: "Not reused or edited" },
];

/** The three checks every capture passes, as on the evidence screens (illustration, no real data). */
export function ChecksIllustration() {
  return (
    <figure className="flex flex-col gap-4 rounded-card border border-line bg-white p-5 shadow-raised">
      <div className="flex items-center justify-between">
        <figcaption className="font-semibold text-ink">Every capture is checked</figcaption>
        <span className="type-caption rounded-pill bg-ok-bg px-2 py-0.5 tracking-normal text-ok-fg">
          Accepted
        </span>
      </div>
      <div aria-hidden className="grid h-52 grid-cols-3 gap-2">
        {CAPTURE_PHOTOS.map(({ photo, position }, i) => (
          <span
            key={photo.src}
            className={cn(
              "relative overflow-hidden rounded-control bg-placeholder",
              i === 4 && "ring-2 ring-navy-900 ring-offset-2",
            )}
          >
            <Image
              src={photo.src}
              alt=""
              width={photo.width}
              height={photo.height}
              sizes="(min-width: 1024px) 140px, 30vw"
              className={cn("size-full object-cover", position)}
            />
          </span>
        ))}
      </div>
      <ul className="flex flex-col gap-2">
        {CHECKS.map(({ icon: Icon, label }) => (
          <li key={label} className="type-small flex items-center justify-between gap-3">
            <span className="flex items-center gap-2 text-ink">
              <Icon aria-hidden strokeWidth={1.75} className="size-4 text-slate" />
              {label}
            </span>
            <span className="flex items-center gap-1 font-semibold text-ok-fg">
              <Check aria-hidden strokeWidth={2} className="size-4" />
              Passed
            </span>
          </li>
        ))}
      </ul>
    </figure>
  );
}

/** A verified milestone waiting for the client's approval (illustration: no names or amounts). */
export function ReleaseIllustration() {
  return (
    <figure className="ibh-on-navy flex flex-col gap-3 rounded-card bg-navy-900 p-5 text-white shadow-raised">
      <figcaption className="type-caption tracking-normal text-x-on-navy-muted uppercase">
        Milestone · verified
      </figcaption>
      <p className="type-h3">Waiting for your approval</p>
      <p className="type-small flex items-center gap-2 text-navy-200">
        <Lock aria-hidden strokeWidth={1.75} className="size-4" />
        Held by a licensed escrow partner, never by iBackHome
      </p>
      <span className="flex min-h-11 items-center justify-center rounded-control bg-white font-semibold text-navy-900">
        Approve release
      </span>
    </figure>
  );
}
