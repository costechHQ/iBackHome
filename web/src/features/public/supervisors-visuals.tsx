import { Camera, MapPin, ShieldCheck } from "lucide-react";
import Image from "next/image";
import Link from "next/link";

import { Button } from "@/common/ui/button";

import { Eyebrow } from "./blocks";
import { PhotoMarquee, type MarqueeItem } from "./photo-marquee";
import { PHOTOS } from "./photos";

// The supervisor page's own visuals (WEB-PUBLIC-005): an animated hero collage and a slow marquee of the
// stages a supervisor checks. Photography is free-licence stock, not iBackHome sites, and the page says so.
// The notice cards use neutral wording, with no sample names or amounts (PACKAGE-REPORT W-37).

export function SupervisorHero({ ratePerVisit }: { ratePerVisit?: string }) {
  return (
    <section className="relative overflow-hidden bg-canvas">
      <div
        aria-hidden
        className="absolute -bottom-40 -left-32 size-136 rounded-full bg-accent-tint opacity-70 blur-3xl"
      />
      <div className="relative mx-auto grid max-w-336 items-center gap-12 px-4 pt-12 pb-16 sm:px-8 lg:grid-cols-2 lg:gap-8 lg:px-12 lg:pt-16 lg:pb-24 xl:px-16">
        <div className="flex flex-col gap-6">
          <div className="ibh-rise self-start">
            <Eyebrow>Become a supervisor</Eyebrow>
          </div>
          <h1 className="type-display ibh-rise text-ink [--ibh-delay:120ms]">
            Be the{" "}
            <span className="relative inline-block whitespace-nowrap">
              eyes on site
              <span
                aria-hidden
                className="ibh-underline absolute inset-x-0 -bottom-1 h-2 rounded-pill bg-accent/30"
              />
            </span>{" "}
            for families abroad
          </h1>
          <p className="type-body-lg ibh-rise max-w-xl text-slate [--ibh-delay:240ms]">
            We&apos;re looking for registered builders and engineers across Nigeria to visit sites, capture
            evidence in our app and verify each stage of work. Paid per visit.
          </p>
          <dl className="type-small ibh-rise flex flex-wrap gap-2 text-slate [--ibh-delay:360ms]">
            {ratePerVisit ? (
              <div className="rounded-pill border border-line bg-white px-3 py-1.5 shadow-card">
                <dt className="inline font-semibold text-ink">Pay </dt>
                <dd className="inline">{ratePerVisit} per visit plus transport</dd>
              </div>
            ) : null}
            <div className="rounded-pill border border-line bg-white px-3 py-1.5 shadow-card">
              <dt className="inline font-semibold text-ink">Where </dt>
              <dd className="inline">Across Nigeria, near where you live</dd>
            </div>
            <div className="rounded-pill border border-line bg-white px-3 py-1.5 shadow-card">
              <dt className="inline font-semibold text-ink">Tool </dt>
              <dd className="inline">Your Android phone</dd>
            </div>
          </dl>
          <div className="ibh-rise flex flex-wrap gap-3 [--ibh-delay:480ms]">
            <Button asChild size="lg">
              <Link href="#apply">How to apply</Link>
            </Button>
            <Button asChild size="lg" variant="outline">
              <Link href="/contact">Tell us you&apos;re interested</Link>
            </Button>
          </div>
        </div>

        <div className="relative mx-auto aspect-5/6 w-full max-w-md lg:max-w-none">
          <div className="ibh-rise absolute top-0 left-0 h-11/12 w-2/3 [--ibh-delay:200ms]">
            <div className="rounded-b-3xl relative size-full overflow-hidden rounded-t-full shadow-raised">
              <Image
                src={PHOTOS.engineerPlans.src}
                alt={PHOTOS.engineerPlans.alt}
                width={PHOTOS.engineerPlans.width}
                height={PHOTOS.engineerPlans.height}
                priority
                sizes="(min-width: 1024px) 380px, 70vw"
                className="ibh-kenburns ibh-focus-50-25 size-full object-cover"
              />
            </div>
          </div>

          <div className="ibh-rise absolute right-0 bottom-0 w-5/12 [--ibh-delay:450ms]">
            <div className="ibh-float rounded-3xl overflow-hidden border-4 border-white shadow-raised">
              <Image
                src={PHOTOS.youngEngineer.src}
                alt={PHOTOS.youngEngineer.alt}
                width={PHOTOS.youngEngineer.width}
                height={PHOTOS.youngEngineer.height}
                sizes="(min-width: 1024px) 260px, 45vw"
                className="ibh-focus-50-25 aspect-square w-full object-cover"
              />
            </div>
          </div>

          <div className="ibh-rise absolute top-1/6 right-0 [--ibh-delay:700ms] sm:-right-4">
            <p className="ibh-float flex items-center gap-3 rounded-card bg-white p-3 pr-4 shadow-raised [--ibh-delay:1s]">
              <span className="flex size-10 items-center justify-center rounded-control bg-ok-bg text-ok-fg">
                <MapPin aria-hidden strokeWidth={1.75} className="size-5" />
              </span>
              <span className="flex flex-col">
                <span className="type-small font-semibold text-ink">Inside the site boundary</span>
                <span className="type-caption tracking-normal text-muted">Captured in the app</span>
              </span>
            </p>
          </div>

          <div className="ibh-rise absolute bottom-1/12 left-0 [--ibh-delay:900ms] sm:-left-2">
            <p className="ibh-float type-small flex items-center gap-2 rounded-pill bg-navy-900 px-4 py-2 font-semibold text-white shadow-raised [--ibh-delay:2s]">
              <Camera aria-hidden strokeWidth={1.75} className="size-4" />
              Stage verified
            </p>
          </div>

          <div className="ibh-rise absolute top-1/2 right-1/6 hidden [--ibh-delay:1100ms] sm:block">
            <p className="ibh-float flex size-12 items-center justify-center rounded-pill bg-white text-accent shadow-raised [--ibh-delay:3s]">
              <ShieldCheck aria-hidden strokeWidth={1.75} className="size-6" />
            </p>
          </div>
        </div>
      </div>
    </section>
  );
}

const SITES: readonly MarqueeItem[] = [
  { photo: PHOTOS.foundation, label: "Foundation", focus: "ibh-focus-50-30" },
  { photo: PHOTOS.sandShovelling, label: "Site preparation", focus: "ibh-focus-50-25" },
  { photo: PHOTOS.hammeringFormwork, label: "Formwork", focus: "ibh-focus-30-25" },
  { photo: PHOTOS.rebarCrew, label: "Steel reinforcement" },
  { photo: PHOTOS.siteCrewScaffold, label: "Scaffolding", focus: "ibh-focus-50-75" },
  { photo: PHOTOS.wheelbarrowEarth, label: "Earthworks" },
  { photo: PHOTOS.smilingCrew, label: "The crew" },
];

export function SitesMarquee() {
  return (
    <PhotoMarquee
      id="sites"
      eyebrow="What you'll see"
      title="From the first trench to the last coat of paint"
      lead="You visit homes at every stage of the build, and your photos are what a family abroad sees of theirs."
      items={SITES}
      note="Photography is illustrative: building sites from stock photography, not iBackHome customers' projects."
    />
  );
}
