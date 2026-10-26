import {
  Camera,
  FileText,
  KeyRound,
  Lock,
  MapPin,
  PackageX,
  Receipt,
  Scale,
  ShieldCheck,
  Images,
  TrendingUp,
  Award,
} from "lucide-react";
import Link from "next/link";

import { Button } from "@/common/ui/button";

import {
  ChecksIllustration,
  CheckList,
  CtaBand,
  Eyebrow,
  Faq,
  FeatureCards,
  ReleaseIllustration,
  Section,
  SectionHead,
  Steps,
} from "./blocks";
import { HeroCarousel } from "./hero-carousel";
import { CitiesSection, HomeBanner, StagesSection } from "./landing-photos";

// WEB-PUBLIC-001 Landing at "/" (static). The design's pilot testimonials are placeholders until real quotes
// are collected with consent, so that section isn't shown; the hero and report illustrations use neutral
// wording, not the design's sample names and amounts (PACKAGE-REPORT W-37).

export const LANDING_FAQ = [
  {
    q: "Is iBackHome a construction company?",
    a: "No. You keep your own contractor. We verify what they claim on site and control when money moves.",
  },
  {
    q: "Who holds my money?",
    a: "A licensed escrow partner. iBackHome never holds client funds. Money is released milestone by milestone, only after verification and your approval.",
  },
  {
    q: "Who are the supervisors?",
    a: "Registered builders and engineers, matched to sites near them. We check their professional registration, NIN and two guarantors, rotate them across sites, and send others on unannounced spot checks.",
  },
  {
    q: "What if I don’t agree a milestone is done?",
    a: "Raise a dispute instead of approving. The release pauses, and our team reviews the evidence with you and your contractor before anything is paid.",
  },
  {
    q: "Can someone send old or borrowed photos?",
    a: "Not through iBackHome. The app has no upload button, every capture must be taken inside your site, and look-alike images are flagged for review.",
  },
  {
    q: "Where do you work?",
    a: "Anywhere in Nigeria. When you set up your project, we match a vetted supervisor near your site.",
  },
  {
    q: "What does it cost?",
    a: (
      <>
        A monthly supervision fee per project plus a small fee on each milestone you fund. See the{" "}
        <Link href="/pricing" className="text-accent underline">
          pricing page
        </Link>{" "}
        for how it’s structured.
      </>
    ),
  },
];

export function Landing() {
  return (
    <>
      <section className="bg-white">
        <div className="mx-auto grid max-w-7xl items-center gap-10 px-4 py-14 sm:px-8 lg:grid-cols-2 lg:py-20">
          <div className="flex flex-col gap-5">
            <p className="type-small flex items-center gap-2 self-start rounded-pill bg-mist px-3 py-1 text-ink">
              <MapPin aria-hidden strokeWidth={1.75} className="size-4" />
              For Nigerians abroad building at home
            </p>
            <h1 className="type-display text-ink">Far from home, never out of sight.</h1>
            <p className="type-body-lg text-slate">
              Verified supervisors capture site evidence that can&apos;t be faked. Your money waits with a
              licensed escrow partner and is released milestone by milestone — only when the work is confirmed
              and you approve.
            </p>
            <div className="flex flex-wrap gap-3">
              <Button asChild size="lg">
                <Link href="/sign-in">Get started</Link>
              </Button>
              <Button asChild size="lg" variant="outline">
                <Link href="/how-it-works">See how it works</Link>
              </Button>
            </div>
            <ul className="type-small flex flex-col gap-1 text-slate">
              <li className="flex items-center gap-2">
                <Lock aria-hidden strokeWidth={1.75} className="size-4" />
                Held by a licensed escrow partner, never by iBackHome
              </li>
              <li className="flex items-center gap-2">
                <ShieldCheck aria-hidden strokeWidth={1.75} className="size-4" />
                Keep your own contractor
              </li>
            </ul>
          </div>
          <HeroCarousel />
        </div>
      </section>

      <CitiesSection />

      <Section tone="mist" labelledBy="problem">
        <SectionHead
          id="problem"
          eyebrow="The problem"
          title="Building from abroad shouldn't cost you your savings"
          lead="You can't see what happens on site. So you send money, ask for photos and hope. That's where it goes wrong."
        />
        <FeatureCards
          items={[
            {
              icon: PackageX,
              title: "Materials go missing",
              body: "Cement, blocks and rods paid for your house end up on someone else’s site.",
            },
            {
              icon: Receipt,
              title: "Quotes get inflated",
              body: "Prices padded well above what materials actually cost locally, with no way for you to check.",
            },
            {
              icon: Images,
              title: "Photos get recycled",
              body: "Old or borrowed pictures arrive as “this week’s progress”, late and looking much like last week’s.",
            },
          ]}
        />
        <p className="text-ink">
          The damage isn&apos;t only financial. When trust breaks, family relationships often break with it.
        </p>
      </Section>

      <Section labelledBy="steps">
        <SectionHead
          id="steps"
          eyebrow="How it works"
          title="Four steps. No money moves without proof."
          action={
            <Link href="/how-it-works" className="rounded-control font-semibold text-accent">
              See the full release flow ›
            </Link>
          }
        />
        <Steps
          items={[
            {
              title: "Set up",
              body: "Invite your own contractor, agree a bill of quantities split into milestones, and pin your site on the map.",
            },
            {
              title: "Verified site visits",
              body: "A vetted, registered supervisor visits on schedule and unannounced, capturing evidence in our app.",
            },
            {
              title: "Milestone approval",
              body: "When your contractor says a stage is done, the supervisor verifies it. Then you review the proof and approve.",
            },
            {
              title: "Escrow release",
              body: "Only then does the licensed escrow partner pay your contractor. Not before.",
            },
          ]}
        />
      </Section>

      <StagesSection />

      <Section labelledBy="proof">
        <div className="grid items-start gap-10 lg:grid-cols-2">
          <div className="flex flex-col gap-6">
            <SectionHead id="proof" eyebrow="Proof, not promises" title="Evidence that can't be faked" />
            <FeatureCards
              columns={2}
              items={[
                {
                  icon: Camera,
                  title: "In-app camera only",
                  body: "There’s no upload button. Photos and videos can only be taken live, in the iBackHome app.",
                },
                {
                  icon: KeyRound,
                  title: "Stamped with place and time",
                  body: "Each capture records where and when it was taken, signed by the supervisor’s registered phone.",
                },
                {
                  icon: MapPin,
                  title: "Inside your site, or rejected",
                  body: "Your site has a boundary on the map. Anything captured outside it is rejected automatically.",
                },
                {
                  icon: Images,
                  title: "Reused photos get caught",
                  body: "Every image is compared with every photo on iBackHome. Look-alikes are flagged for our team to review.",
                },
              ]}
            />
          </div>
          <ChecksIllustration />
        </div>
      </Section>

      <Section tone="navy" labelledBy="escrow">
        <div className="grid items-center gap-8 lg:grid-cols-2">
          <SectionHead
            id="escrow"
            eyebrow="The escrow promise"
            title="Your money waits until the work is proven"
            onDark
          />
          <ReleaseIllustration />
        </div>
        <FeatureCards
          onDark
          items={[
            {
              icon: Lock,
              title: "Never held by iBackHome",
              body: "Your money sits with a licensed escrow partner from the moment you pay.",
            },
            {
              icon: KeyRound,
              title: "Two keys to release",
              body: "A milestone is paid only after the supervisor verifies it and you approve it.",
            },
            {
              icon: Scale,
              title: "Disagree? It pauses",
              body: "Raise a dispute instead of approving. Nothing is released until it’s resolved.",
            },
          ]}
        />
        <p className="text-navy-200">
          Pay in GBP, USD or EUR. Your contractor is paid in naira, at the exchange rate recorded on the day
          you fund.{" "}
          <Link href="/trust" className="text-white underline">
            How escrow works
          </Link>
        </p>
      </Section>

      <Section labelledBy="report">
        <div className="grid items-center gap-10 lg:grid-cols-2">
          <div className="flex flex-col gap-5">
            <SectionHead
              id="report"
              eyebrow="Every Friday"
              title="A weekly report built only from facts"
              lead="AI drafts a plain-language summary of your week from your project's own evidence, verifications and payments. Your supervisor checks it before it reaches you."
            />
            <CheckList
              items={[
                "Points to the photos it’s based on",
                "Money figures come straight from the payment record",
                "Checked by your supervisor before it’s sent",
                "Arrives on WhatsApp and email, in your time zone",
              ]}
            />
          </div>
          <figure className="flex flex-col gap-3 rounded-card border border-line bg-white p-5 shadow-raised">
            <div className="flex flex-wrap gap-2">
              <span className="type-caption rounded-pill bg-accent-tint px-2 py-0.5 tracking-normal text-info-fg">
                AI-generated report
              </span>
              <span className="type-caption rounded-pill bg-ok-bg px-2 py-0.5 tracking-normal text-ok-fg">
                Reviewed by your supervisor
              </span>
            </div>
            <p className="flex items-center gap-2 font-semibold text-ink">
              <FileText aria-hidden strokeWidth={1.75} className="size-4" />
              Your weekly report
            </p>
            <p className="text-slate">
              What was done on site this week, each point linked to the photo behind it, and what is waiting
              for your approval.
            </p>
            <figcaption className="type-small text-muted">
              AI drafts and checks — it never approves, releases or pays.
            </figcaption>
          </figure>
        </div>
      </Section>

      <Section tone="mist" labelledBy="contractors">
        <div className="grid items-center gap-8 rounded-card border border-line bg-white p-6 shadow-card lg:grid-cols-3 lg:p-10">
          <div className="flex flex-col gap-3">
            <Eyebrow>For contractors</Eyebrow>
            <h2 id="contractors" className="type-h2 text-ink">
              Good contractors get paid faster
            </h2>
            <p className="text-slate">
              Honest builders lose time waiting for clients who can&apos;t see their work. With iBackHome, the
              proof travels with the claim.
            </p>
            <Button asChild variant="outline" className="self-start">
              <Link href="/contractors">For contractors</Link>
            </Button>
          </div>
          <div className="lg:col-span-2">
            <FeatureCards
              columns={2}
              items={[
                {
                  icon: TrendingUp,
                  title: "Faster payment",
                  body: "Verified milestones are approved sooner, and the escrow partner pays you in naira.",
                },
                {
                  icon: Award,
                  title: "A track record",
                  body: "Every verified milestone builds a record you can show the next client.",
                },
              ]}
            />
          </div>
        </div>
      </Section>

      <HomeBanner />

      <Section labelledBy="faq" className="max-w-3xl">
        <h2 id="faq" className="type-h1 text-ink">
          Questions people ask
        </h2>
        <Faq items={LANDING_FAQ} />
      </Section>

      <CtaBand
        title="Build at home with proof, not promises"
        lead="Start with your site address and your contractor's phone number. We'll handle the rest with you."
        secondary={{ label: "Talk to us", href: "/contact" }}
      />
    </>
  );
}
