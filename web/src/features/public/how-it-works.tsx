import { CalendarClock, FileText, Scale, TriangleAlert } from "lucide-react";
import Image from "next/image";

import { CtaBand, FeatureCards, Section, SectionHead, Steps } from "./blocks";
import { HowHero } from "./how-it-works-visuals";
import { PHOTOS } from "./photos";
import { ReportInterface } from "./report-interface";
import { Reveal } from "./reveal";

// WEB-PUBLIC-002 How it works. Contractors are invited by phone (the backend invites by phone only), and the
// budget is in naira while the client pays each milestone in GBP, USD or EUR (PACKAGE-REPORT B-6, W-37).

const ROLES = [
  {
    who: "You",
    does: "Fund milestones, review evidence, approve or dispute.",
    never: "Has to take anyone’s word for it.",
  },
  {
    who: "Your contractor",
    does: "Prices the work, builds, claims milestones.",
    never: "Approves their own work or sees spot checks coming.",
  },
  {
    who: "Supervisor",
    does: "Visits, captures evidence, verifies each stage.",
    never: "Supervises a relative’s project or approves payment.",
  },
  {
    who: "iBackHome team",
    does: "Vets supervisors, reviews flags, resolves disputes.",
    never: "Holds your money.",
  },
  {
    who: "Escrow partner",
    does: "Holds funds and pays out on release.",
    never: "Releases without both approvals.",
  },
];

export function HowItWorks() {
  return (
    <>
      <HowHero
        title="Every payment waits for proof"
        lead="Your contractor builds. A vetted supervisor checks. You decide. A licensed escrow partner pays — and only when both the supervisor and you have said yes."
      />
      <Section tone="mist" labelledBy="flow">
        <div className="grid items-start gap-8 lg:grid-cols-2 lg:gap-12">
          <div className="flex flex-col gap-8">
            <SectionHead id="flow" title="How a milestone gets paid" />
            <ol className="grid gap-4 sm:grid-cols-2">
              {[
                ["Contractor claims the stage", "Your contractor says a milestone is finished."],
                ["Supervisor captures evidence", "On site, in the iBackHome app only."],
                [
                  "Three checks",
                  "Every photo and video, automatically: inside your site, device-signed, not reused.",
                ],
                ["Supervisor verifies", "Checks the stage against the agreed checklist."],
                ["You approve", "From your phone, in three taps."],
                ["Escrow partner pays", "Your contractor receives naira. You get a receipt."],
              ].map(([title, body], i) => (
                <li key={title} className="flex">
                  <Reveal delay={(i % 2) * 120} className="flex w-full">
                    <div className="flex w-full flex-col gap-1 rounded-card border border-line bg-white p-5 shadow-card transition-transform duration-300 hover:-translate-y-1">
                      <span className="type-caption text-muted uppercase">Step {i + 1}</span>
                      <h3 className="type-h3 text-ink">{title}</h3>
                      <p className="text-slate">{body}</p>
                    </div>
                  </Reveal>
                </li>
              ))}
            </ol>
          </div>
          <Reveal
            delay={120}
            className="group overflow-hidden rounded-card shadow-raised lg:sticky lg:top-24"
          >
            <Image
              src={PHOTOS.engineerTape.src}
              alt={PHOTOS.engineerTape.alt}
              width={PHOTOS.engineerTape.width}
              height={PHOTOS.engineerTape.height}
              sizes="(min-width: 1024px) 560px, 100vw"
              className="ibh-focus-50-30 aspect-4/5 w-full object-cover transition-transform duration-1000 ease-out group-hover:scale-105"
            />
          </Reveal>
        </div>
        <FeatureCards
          animate
          columns={2}
          items={[
            {
              icon: TriangleAlert,
              title: "If a check fails",
              body: "Outside your site, wrong phone or wrong clock: rejected. A possible reused photo: flagged for our team. Either way it can't count — the supervisor captures again.",
            },
            {
              icon: Scale,
              title: "If you disagree",
              body: "Raise a dispute instead of approving. The release pauses. Our team reviews the evidence with you and your contractor, and two staff sign off the outcome: pay the milestone, or send it back for rework.",
            },
          ]}
        />
        <p className="text-slate">
          The supervisor can also send a claim back for rework at step 4. Contractor photos are shown to you
          for context but never count toward verification.
        </p>
      </Section>
      <Section labelledBy="setup">
        <div className="grid items-start gap-8 lg:grid-cols-2 lg:gap-12">
          <div className="flex flex-col gap-8">
            <SectionHead
              id="setup"
              eyebrow="Before the first milestone"
              title="Setting up takes a few days, not weeks"
            />
            <Steps
              animate
              columns={2}
              items={[
                { title: "Create your project", body: "Your site address and a budget." },
                {
                  title: "Invite your contractor",
                  body: "By their phone number. They sign in with a one-time code.",
                },
                {
                  title: "Agree the bill of quantities",
                  body: "Your contractor prices the work in milestones. We check it against current market prices.",
                },
                {
                  title: "Pin your site",
                  body: "Mark the plot on the map. Evidence from outside it won’t count.",
                },
                {
                  title: "Fund the first milestone",
                  body: "Pay by card in GBP, USD or EUR. The money goes straight to escrow.",
                },
              ]}
            />
          </div>
          <Reveal
            delay={120}
            className="group overflow-hidden rounded-card shadow-raised lg:sticky lg:top-24 lg:order-first"
          >
            <Image
              src={PHOTOS.womenEngineers.src}
              alt={PHOTOS.womenEngineers.alt}
              width={PHOTOS.womenEngineers.width}
              height={PHOTOS.womenEngineers.height}
              sizes="(min-width: 1024px) 560px, 100vw"
              className="aspect-4/3 w-full object-cover transition-transform duration-1000 ease-out group-hover:scale-105"
            />
          </Reveal>
        </div>
      </Section>
      <Section tone="mist" labelledBy="during">
        <div className="grid items-stretch gap-8 lg:grid-cols-2 lg:gap-12">
          <div className="flex flex-col gap-8">
            <SectionHead id="during" eyebrow="While the work goes on" title="You see it as it happens" />
            <FeatureCards
              animate
              columns={1}
              items={[
                {
                  icon: FileText,
                  title: "A weekly report, every Friday",
                  body: "AI drafts it from your project's evidence, verifications and payments; your supervisor checks it; you get it on WhatsApp, email and your dashboard. Every claim links to the photo behind it.",
                },
                {
                  icon: CalendarClock,
                  title: "Unannounced spot checks",
                  body: "From time to time we send a different supervisor, without telling the contractor, to compare what's on site with what's been claimed.",
                },
              ]}
            />
          </div>
          <Reveal delay={120} className="flex">
            <ReportInterface />
          </Reveal>
        </div>
      </Section>
      <Section labelledBy="roles">
        <Reveal>
          <SectionHead id="roles" title="Who does what" />
        </Reveal>
        <div
          role="region"
          aria-label="Who does what"
          tabIndex={0}
          className="overflow-x-auto rounded-card border border-line"
        >
          <table className="w-full border-collapse text-left">
            <caption className="sr-only">Who does what</caption>
            <thead>
              <tr className="type-caption text-muted uppercase">
                <th scope="col" className="border-b border-line px-4 py-3">
                  Who
                </th>
                <th scope="col" className="border-b border-line px-4 py-3">
                  Does
                </th>
                <th scope="col" className="border-b border-line px-4 py-3">
                  Never
                </th>
              </tr>
            </thead>
            <tbody>
              {ROLES.map((r) => (
                <tr key={r.who} className="border-b border-line last:border-b-0">
                  <th scope="row" className="px-4 py-3 font-semibold text-ink">
                    {r.who}
                  </th>
                  <td className="px-4 py-3 text-slate">{r.does}</td>
                  <td className="px-4 py-3 text-slate">{r.never}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </Section>
      <p className="type-small mx-auto w-full max-w-336 px-4 pb-6 text-muted sm:px-8 lg:px-12 xl:px-16">
        Photography is illustrative: stock photography, not iBackHome customers or sites.
      </p>
      <CtaBand title="Ready to see your site from wherever you are?" />
    </>
  );
}
