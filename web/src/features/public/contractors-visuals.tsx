import { BadgeCheck, Banknote, FileCheck2, ShieldCheck } from "lucide-react";
import Image from "next/image";
import Link from "next/link";

import { Button } from "@/common/ui/button";

import { Eyebrow } from "./blocks";
import { PHOTOS } from "./photos";
import { PhotoMarquee, type MarqueeItem } from "./photo-marquee";

// The contractor page's own visuals (WEB-PUBLIC-004): an animated hero collage and a slow marquee of finished
// homes. Photography is free-licence stock, not iBackHome customers' projects, and the page says so. The notice
// cards use neutral wording, with no sample names or amounts (PACKAGE-REPORT W-37).

const HERO_POINTS = [
  { icon: Banknote, label: "Paid in naira" },
  { icon: FileCheck2, label: "Proof travels with your claim" },
  { icon: BadgeCheck, label: "A record of good work" },
];

export function ContractorHero() {
  return (
    <section className="relative overflow-hidden bg-canvas">
      <div
        aria-hidden
        className="absolute -top-32 -right-32 size-136 rounded-full bg-accent-tint opacity-70 blur-3xl"
      />
      <div className="relative mx-auto grid max-w-336 items-center gap-12 px-4 pt-12 pb-16 sm:px-8 lg:grid-cols-2 lg:gap-8 lg:px-12 lg:pt-16 lg:pb-24 xl:px-16">
        <div className="flex flex-col gap-6">
          <div className="ibh-rise self-start">
            <Eyebrow>For contractors</Eyebrow>
          </div>
          <h1 className="type-display ibh-rise text-ink [--ibh-delay:120ms]">
            Do honest work.{" "}
            <span className="relative inline-block whitespace-nowrap">
              Get paid
              <span
                aria-hidden
                className="ibh-underline absolute inset-x-0 -bottom-1 h-2 rounded-pill bg-accent/30"
              />
            </span>{" "}
            without the wait.
          </h1>
          <p className="type-body-lg ibh-rise max-w-xl text-slate [--ibh-delay:240ms]">
            Clients abroad pay faster when they can see the proof. iBackHome gives them that — and gives you a
            record of every stage done right.
          </p>
          <div className="ibh-rise flex flex-wrap gap-3 [--ibh-delay:360ms]">
            <Button asChild size="lg">
              <Link href="#join">How to join</Link>
            </Button>
            <Button asChild size="lg" variant="outline">
              <Link href="/how-it-works">See the release flow</Link>
            </Button>
          </div>
          <ul className="ibh-rise type-small flex flex-wrap gap-2 text-ink [--ibh-delay:480ms]">
            {HERO_POINTS.map(({ icon: Icon, label }) => (
              <li
                key={label}
                className="flex items-center gap-2 rounded-pill border border-line bg-white px-3 py-1.5 shadow-card"
              >
                <Icon aria-hidden strokeWidth={1.75} className="size-4 text-accent" />
                {label}
              </li>
            ))}
          </ul>
        </div>

        <div className="relative mx-auto aspect-5/6 w-full max-w-md lg:max-w-none">
          <div className="ibh-rise absolute top-0 right-0 h-11/12 w-2/3 [--ibh-delay:200ms]">
            <div className="rounded-b-3xl relative size-full overflow-hidden rounded-t-full shadow-raised">
              <Image
                src={PHOTOS.engineerPhone.src}
                alt={PHOTOS.engineerPhone.alt}
                width={PHOTOS.engineerPhone.width}
                height={PHOTOS.engineerPhone.height}
                priority
                sizes="(min-width: 1024px) 380px, 70vw"
                className="ibh-kenburns ibh-focus-50-25 size-full object-cover"
              />
            </div>
          </div>

          <div className="ibh-rise absolute bottom-0 left-0 w-7/12 [--ibh-delay:450ms]">
            <div className="ibh-float rounded-3xl overflow-hidden border-4 border-white shadow-raised">
              <Image
                src={PHOTOS.duplexDusk.src}
                alt={PHOTOS.duplexDusk.alt}
                width={PHOTOS.duplexDusk.width}
                height={PHOTOS.duplexDusk.height}
                sizes="(min-width: 1024px) 320px, 55vw"
                className="ibh-focus-50-72 aspect-4/3 w-full object-cover"
              />
            </div>
          </div>

          <div className="ibh-rise absolute top-1/6 left-0 [--ibh-delay:700ms] sm:-left-4">
            <p className="ibh-float flex items-center gap-3 rounded-card bg-white p-3 pr-4 shadow-raised [--ibh-delay:1s]">
              <span className="flex size-10 items-center justify-center rounded-control bg-ok-bg text-ok-fg">
                <BadgeCheck aria-hidden strokeWidth={1.75} className="size-5" />
              </span>
              <span className="flex flex-col">
                <span className="type-small font-semibold text-ink">Milestone verified</span>
                <span className="type-caption tracking-normal text-muted">Paid in naira</span>
              </span>
            </p>
          </div>

          <div className="ibh-rise absolute right-2 bottom-1/12 [--ibh-delay:900ms] sm:-right-2">
            <p className="ibh-float type-small flex items-center gap-2 rounded-pill bg-navy-900 px-4 py-2 font-semibold text-white shadow-raised [--ibh-delay:2s]">
              <ShieldCheck aria-hidden strokeWidth={1.75} className="size-4" />
              Supervisor checked
            </p>
          </div>
        </div>
      </div>
    </section>
  );
}

const HOMES: readonly MarqueeItem[] = [
  { photo: PHOTOS.abujaModernHome, label: "Family home", focus: "ibh-focus-50-40" },
  { photo: PHOTOS.duplexDusk, label: "Modern duplex", focus: "ibh-focus-50-72" },
  { photo: PHOTOS.abujaBungalow, label: "Arched bungalow" },
  { photo: PHOTOS.villaPool, label: "Courtyard home" },
  { photo: PHOTOS.duplexWhite, label: "White duplex" },
  { photo: PHOTOS.abujaHouse, label: "Three-storey house", focus: "ibh-focus-50-30" },
];

export function HomesMarquee() {
  return (
    <PhotoMarquee
      id="homes"
      eyebrow="The homes you'll build"
      title="Homes families are proud to come back to"
      lead="A client abroad trusts the contractor whose work they can see. Every verified milestone adds to a record of homes done right."
      items={HOMES}
      note="Photography is illustrative: homes and sites from stock photography, not iBackHome customers' projects."
    />
  );
}
