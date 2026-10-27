import Image from "next/image";
import Link from "next/link";

import { Button } from "@/common/ui/button";

import { Eyebrow, Section, SectionHead } from "./blocks";
import { PHOTOS, type Photo } from "./photos";
import { Reveal } from "./reveal";
import { StageScroller, type Stage } from "./stage-scroller";

// The photo-led segments of the landing page (WEB-PUBLIC-001): Nigerian cities, the stages of a build, and a
// closing banner. The pictures are stock photography of real Nigerian homes and building sites, not customers'
// projects, and the page says so.

const CITIES: readonly { name: string; line: string; photo: Photo }[] = [
  { name: "Enugu", line: "Hills, lakes and a growing number of family homes.", photo: PHOTOS.enuguAerial },
  {
    name: "Abuja",
    line: "Estates and family houses in the shadow of Zuma Rock.",
    photo: PHOTOS.abujaZumaRock,
  },
  {
    name: "Lagos",
    line: "Apartment blocks and compounds rising beside the road.",
    photo: PHOTOS.lagosAerial,
  },
  {
    name: "Port Harcourt",
    line: "Riverside homes and new builds on the delta.",
    photo: PHOTOS.portHarcourtAerial,
  },
];

const STAGES: readonly Stage[] = [
  {
    title: "Foundation",
    body: "Trenches dug and the first course of blocks laid. Your supervisor photographs depth and levels.",
    photo: PHOTOS.foundation,
  },
  {
    title: "Materials on site",
    body: "Sandcrete blocks, sand and cement counted against your bill of quantities.",
    photo: PHOTOS.sandcrete,
  },
  {
    title: "Blockwork",
    body: "Walls rise course by course, each lift photographed inside your site boundary.",
    photo: PHOTOS.blockwork,
  },
  {
    title: "Steel and formwork",
    body: "Reinforcement and shuttering are checked before a single bag of concrete is poured.",
    photo: PHOTOS.formwork,
  },
  {
    title: "Slab and roof",
    body: "The slab and roof go up. The supervisor verifies the stage before you are asked to approve.",
    photo: PHOTOS.roofing,
  },
  {
    title: "Finishing",
    body: "Plaster, paint and fittings. The last milestone is verified and released like every other.",
    photo: PHOTOS.abujaHouse,
  },
];

export function CitiesSection() {
  return (
    <Section labelledBy="cities">
      <Reveal>
        <SectionHead
          id="cities"
          eyebrow="Anywhere in Nigeria"
          title="From Enugu to Lagos, Abuja to Port Harcourt"
          lead="Wherever your plot is, you can see it going up. We match a vetted supervisor to the site, not to a city."
        />
      </Reveal>
      <ul className="grid gap-4 sm:grid-cols-2 lg:grid-cols-4">
        {CITIES.map(({ name, line, photo }, i) => (
          <li key={name}>
            <Reveal delay={i * 120}>
              <figure className="group relative aspect-4/5 overflow-hidden rounded-card bg-navy-900 shadow-card">
                <Image
                  src={photo.src}
                  alt={photo.alt}
                  width={photo.width}
                  height={photo.height}
                  sizes="(min-width: 1024px) 300px, (min-width: 640px) 50vw, 100vw"
                  className="size-full object-cover transition-transform duration-700 ease-out group-hover:scale-110"
                />
                <div className="absolute inset-0 bg-linear-to-t from-navy-900/90 via-navy-900/20 to-transparent" />
                <figcaption className="absolute inset-x-0 bottom-0 flex flex-col gap-1 p-4 text-white">
                  <span className="type-h3">{name}</span>
                  <span className="type-small text-navy-200">{line}</span>
                </figcaption>
              </figure>
            </Reveal>
          </li>
        ))}
      </ul>
      <p className="type-small text-muted">
        Photography is illustrative: real Nigerian homes and building sites, not iBackHome customers&apos;
        projects.
      </p>
    </Section>
  );
}

export function StagesSection() {
  return (
    <Section tone="mist" labelledBy="stages">
      <Reveal>
        <SectionHead
          id="stages"
          eyebrow="Foundation to finishing"
          title="See every stage as it happens"
          lead="Your bill of quantities sets your milestones. At each one, a supervisor on site captures the proof before any money moves."
        />
      </Reveal>
      <Reveal delay={150}>
        <StageScroller stages={STAGES} />
      </Reveal>
    </Section>
  );
}

export function HomeBanner() {
  return (
    <Section tone="navy" labelledBy="home">
      <div className="grid items-center gap-10 lg:grid-cols-2">
        <Reveal className="flex flex-col gap-5">
          <Eyebrow onDark>For the family you&apos;re building for</Eyebrow>
          <h2 id="home" className="type-h1 text-white">
            Come home to a house you watched go up
          </h2>
          <p className="type-body-lg text-navy-200">
            Every milestone has its photos, its place on the map and its date. When you land in Nigeria, the
            house is the one you approved, stage by stage.
          </p>
          <div className="flex flex-wrap gap-3">
            <Button asChild size="lg" variant="white-on-navy">
              <Link href="/sign-in">Get started</Link>
            </Button>
            <Button asChild size="lg" variant="outline-on-navy">
              <Link href="/how-it-works">See how it works</Link>
            </Button>
          </div>
        </Reveal>
        <Reveal delay={150} className="mx-auto w-full max-w-sm">
          {/* A silent, looping video. The family photo shows while it loads, and instead of it for visitors who ask for less motion. */}
          <figure className="relative aspect-4/5 overflow-hidden rounded-card bg-navy-800 shadow-raised">
            <Image
              src={PHOTOS.family.src}
              alt={PHOTOS.family.alt}
              width={PHOTOS.family.width}
              height={PHOTOS.family.height}
              sizes="(min-width: 1024px) 384px, 90vw"
              className="hidden size-full object-cover motion-reduce:block"
            />
            <video
              aria-hidden
              autoPlay
              muted
              loop
              playsInline
              poster={PHOTOS.family.src}
              className="absolute inset-0 size-full object-cover motion-reduce:hidden"
            >
              <source src="/landing/sign-in-bg.mp4" type="video/mp4" />
            </video>
          </figure>
        </Reveal>
      </div>
    </Section>
  );
}
