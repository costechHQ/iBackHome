import { Award, MessageSquareOff, PackageCheck, TrendingUp } from "lucide-react";
import Image from "next/image";
import Link from "next/link";

import { Button } from "@/common/ui/button";

import { CheckList, CtaBand, Faq, FeatureCards, Section, SectionHead, Steps } from "./blocks";
import { ContractorHero, HomesMarquee } from "./contractors-visuals";
import { PHOTOS } from "./photos";
import { Reveal } from "./reveal";
import { SITE } from "./site";
import { SitesMarquee, SupervisorHero } from "./supervisors-visuals";

// WEB-PUBLIC-004 For contractors and WEB-PUBLIC-005 Become a supervisor. Contractors join when a client adds
// their phone number to a project (no invitation link is sent yet, and no email invite exists), so the steps
// say to sign in with that number. Supervisors apply in the Android app, which isn't published yet, so the
// page explains the role and points to the contact channel; rates and timings appear once site.ts has them
// (PACKAGE-REPORT W-37).

export function ForContractors() {
  const c = SITE.contractors;
  const faq = [
    {
      q: "How am I paid?",
      a: `By the licensed escrow partner, in naira, after the supervisor verifies the milestone and your client approves it.${c.payout ? ` ${c.payout}` : ""}`,
    },
    ...(c.fee ? [{ q: "Is there a fee for contractors?", a: c.fee }] : []),
    {
      q: "What if the supervisor rejects my claim?",
      a: "You’ll see the reason. Fix what’s needed and claim again. If you think the rejection is wrong, raise it with our team and we’ll review the evidence.",
    },
    {
      q: "Do I get told about spot checks?",
      a: "No. Spot checks are unannounced by design — that’s what makes your verified milestones worth trusting.",
    },
  ];
  return (
    <>
      <ContractorHero />
      <HomesMarquee />
      <Section tone="mist" labelledBy="why">
        <Reveal>
          <SectionHead id="why" title="Why good contractors like being supervised" />
        </Reveal>
        <FeatureCards
          animate
          columns={4}
          items={[
            {
              icon: TrendingUp,
              title: "Faster payment",
              body: "When the supervisor verifies a stage, your client sees the proof straight away and can approve from their phone. The escrow partner pays you in naira.",
            },
            {
              icon: MessageSquareOff,
              title: "Fewer arguments",
              body: "“Is it done?” is settled by an independent supervisor and photos taken on site — not by long calls across time zones.",
            },
            {
              icon: Award,
              title: "A record of good work",
              body: "Every verified, paid milestone builds a track record you can show your next client.",
            },
            {
              icon: PackageCheck,
              title: "Materials delivered",
              body: "Request cement, blocks and rods from verified suppliers. Your client approves, the supplier delivers to site and is paid directly.",
            },
          ]}
        />
      </Section>
      <section aria-label="A track record" className="bg-white px-4 pt-14 sm:px-8 lg:px-12 lg:pt-20 xl:px-16">
        <Reveal className="group relative mx-auto aspect-4/5 max-w-336 overflow-hidden rounded-card shadow-raised sm:aspect-16/9 lg:aspect-21/9">
          <Image
            src={PHOTOS.siteLeadRoad.src}
            alt={PHOTOS.siteLeadRoad.alt}
            width={PHOTOS.siteLeadRoad.width}
            height={PHOTOS.siteLeadRoad.height}
            sizes="(min-width: 1280px) 1216px, 100vw"
            className="ibh-focus-50-30 size-full object-cover transition-transform duration-1000 ease-out group-hover:scale-105"
          />
          <div className="absolute inset-0 bg-linear-to-r from-navy-900/85 via-navy-900/50 to-transparent" />
          <div className="ibh-on-navy absolute inset-y-0 left-0 flex max-w-2xl flex-col justify-center gap-4 p-6 sm:p-10 lg:p-14">
            <p className="type-caption text-x-on-navy-muted uppercase">A record of good work</p>
            <p className="type-h1 text-white">
              Every verified, paid milestone builds a track record you can show your next client.
            </p>
            <Button asChild variant="white-on-navy" className="self-start">
              <Link href="#join">How to join</Link>
            </Button>
          </div>
        </Reveal>
      </section>
      <Section labelledBy="join">
        <Reveal>
          <SectionHead id="join" title="How it works for you" />
        </Reveal>
        <Steps
          animate
          items={[
            {
              tag: "Phone",
              title: "Sign in",
              body: "Your client adds your phone number to their project. Sign in with that number and a one-time code.",
            },
            {
              tag: "Web",
              title: "Price the work",
              body: "Enter your bill of quantities, grouped into milestones.",
            },
            { tag: "Phone", title: "Build and claim", body: "When a stage is finished, claim it." },
            {
              tag: "On site",
              title: "Supervisor verifies",
              body: "An independent supervisor checks the work against the checklist.",
            },
            {
              tag: "Bank",
              title: "Get paid",
              body: "Once your client approves, the escrow partner pays you in naira.",
            },
          ]}
        />
        <div className="grid gap-6 lg:grid-cols-2">
          <div className="flex flex-col gap-3">
            <h3 className="type-h3 text-ink">What we ask of you</h3>
            <CheckList
              items={[
                "Let supervisors visit, including unannounced spot checks.",
                "Take any photos you share in the iBackHome app — there's no upload from your gallery.",
                "Expect your quote to be compared with current market prices. Fair prices pass quietly.",
                "If you disagree with a rejection, raise it with our team rather than with the client directly.",
              ]}
            />
          </div>
          <div className="flex flex-col gap-3 overflow-hidden rounded-card bg-canvas">
            <Image
              src={PHOTOS.youngEngineer.src}
              alt={PHOTOS.youngEngineer.alt}
              width={PHOTOS.youngEngineer.width}
              height={PHOTOS.youngEngineer.height}
              sizes="(min-width: 1024px) 560px, 100vw"
              className="ibh-focus-50-25 h-56 w-full object-cover"
            />
            <div className="flex flex-col gap-3 p-6 pt-3">
              <h3 className="type-h3 text-ink">Contractors join through their client</h3>
              <p className="text-slate">
                Your client creates the project and adds you by your phone number. Sign in with that number
                and a one-time code — no password.
              </p>
              <div className="flex flex-wrap gap-3">
                <Button asChild>
                  <Link href="/sign-in">I&apos;ve been added — sign in</Link>
                </Button>
                <Button asChild variant="outline">
                  <Link href="/contact">Tell us about a client project</Link>
                </Button>
              </div>
            </div>
          </div>
        </div>
      </Section>
      <Section tone="mist" labelledBy="contractor-faq" className="max-w-3xl">
        <h2 id="contractor-faq" className="type-h1 text-ink">
          Contractor questions
        </h2>
        <Faq items={faq} />
      </Section>
    </>
  );
}

export function BecomeASupervisor() {
  const s = SITE.supervisors;
  const faq = [
    {
      q: "Does the app work without signal?",
      a: "Yes. You can capture with no signal; the app keeps each photo’s original time and place and uploads when you’re back online. Upload within 72 hours of capture.",
    },
    {
      q: "Can I use photos from my gallery?",
      a: "No. The app only accepts photos and video taken with its own camera, inside the site boundary. That’s what makes your evidence trustworthy.",
    },
    ...(s.payment ? [{ q: "How am I paid?", a: s.payment }] : []),
    {
      q: "What if I’m turned down?",
      a: "You’ll see the reason in the app and can apply again once it’s fixed.",
    },
  ];
  return (
    <>
      <SupervisorHero ratePerVisit={s.ratePerVisit || undefined} />
      <SitesMarquee />
      <Section tone="mist" labelledBy="who">
        <Reveal className="grid gap-10 lg:grid-cols-2">
          <div className="flex flex-col gap-4">
            <h2 id="who" className="type-h2 text-ink">
              Who we&apos;re looking for
            </h2>
            <CheckList
              items={[
                "Registered engineer (COREN) or builder (NIOB)",
                "A valid NIN",
                "Two guarantors we can contact",
                "An Android phone (Android 8 or later) with a working camera and GPS",
                "Able to reach building sites near where you live",
                "Willing to declare any relatives who work as contractors",
              ]}
            />
          </div>
          <div className="flex flex-col gap-4">
            <h2 className="type-h2 text-ink">What you&apos;ll do</h2>
            <dl className="grid gap-3 sm:grid-cols-2">
              {[
                ["Scheduled visits", "Visit your assigned sites and capture what you see."],
                ["Spot checks", "Unannounced visits to other supervisors’ sites."],
                ["Capture evidence", "Photos and video in the app — it works offline."],
                ["Verify milestones", "Check each stage against its checklist, or send it back."],
                ["Confirm deliveries", "Count materials delivered to site."],
                ["Review reports", "Check the weekly AI draft before the client sees it."],
              ].map(([t, d]) => (
                <div key={t} className="rounded-card border border-line bg-white p-4">
                  <dt className="font-semibold text-ink">{t}</dt>
                  <dd className="type-small text-slate">{d}</dd>
                </div>
              ))}
            </dl>
          </div>
        </Reveal>
      </Section>
      <Section labelledBy="independence">
        <div className="grid items-center gap-8 lg:grid-cols-2">
          <Reveal className="group overflow-hidden rounded-card shadow-raised">
            <Image
              src={PHOTOS.siteCrewScaffold.src}
              alt={PHOTOS.siteCrewScaffold.alt}
              width={PHOTOS.siteCrewScaffold.width}
              height={PHOTOS.siteCrewScaffold.height}
              sizes="(min-width: 1024px) 560px, 100vw"
              className="ibh-focus-50-75 aspect-4/3 w-full object-cover transition-transform duration-1000 ease-out group-hover:scale-105"
            />
          </Reveal>
          <Reveal delay={150}>
            <SectionHead
              id="independence"
              title="Independence is the job"
              lead="Clients trust your verification because nobody can lean on it. These rules protect you as much as them."
            />
          </Reveal>
        </div>
        <FeatureCards
          animate
          columns={4}
          items={[
            {
              title: "No relatives’ projects",
              body: "You’ll never be assigned to, or spot-check, a project run by a contractor you’ve declared as family.",
            },
            {
              title: "Rotation",
              body: "Supervisors rotate after two consecutive milestones on the same project.",
            },
            {
              title: "Checked by others",
              body: "Other supervisors make unannounced spot checks on every site, including yours.",
            },
            {
              title: "You never touch money",
              body: "You verify work. Payments are approved by the client and made by the escrow partner.",
            },
          ]}
        />
      </Section>
      <Section tone="mist" labelledBy="apply">
        <Reveal>
          <SectionHead
            id="apply"
            title="How to apply"
            lead="Applications open in the iBackHome supervisor app, where you'll see your vetting status as each check is completed. The app isn't published yet: get in touch and we'll tell you when it is."
          />
        </Reveal>
        <Steps
          animate
          items={[
            { title: "Sign up in the app", body: "With your phone number and a one-time code." },
            {
              title: "Send your details",
              body: "Registration number, NIN, two guarantors and any relatives in construction.",
            },
            {
              title: "We check",
              body: `Our team verifies each item.${s.vettingTime ? ` ${s.vettingTime}` : ""}`,
            },
            { title: "Get your first site", body: "Once approved, ops assigns you a site near you." },
          ]}
        />
        <Button asChild size="lg" className="self-start">
          <Link href="/contact">Tell us you&apos;re interested</Link>
        </Button>
      </Section>
      <Section labelledBy="supervisor-faq" className="max-w-3xl">
        <h2 id="supervisor-faq" className="type-h1 text-ink">
          Supervisor questions
        </h2>
        <Faq items={faq} />
      </Section>
      <CtaBand
        title="Building from abroad?"
        lead="Start with your site address and your contractor's phone number."
      />
    </>
  );
}
