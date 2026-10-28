import { Lock } from "lucide-react";
import Image from "next/image";

import { Alert } from "@/common/ui/alert";
import { ToneChip } from "@/common/ui/status-chip";

import { CheckList, CtaBand, Faq, Section, SectionHead } from "./blocks";
import { PHOTOS } from "./photos";
import { PricingHero } from "./pricing-visuals";
import { Reveal } from "./reveal";
import { hasPrices, SITE } from "./site";

// WEB-PUBLIC-003 Pricing. Every price on the design is a placeholder, so until site.ts has them the page says
// pricing is being finalised and shows what's included. The backend charges its fee when a milestone is
// funded (FUNDING_FEE_BPS), not on release, so the copy says "funding fee" (PACKAGE-REPORT B-8). The design's
// funding example (sample amounts, "[£ FEE]") isn't shown. Add-ons other than materials are P2 "coming soon".

export function Pricing() {
  const p = SITE.pricing;
  const priced = hasPrices();
  const faq = [
    {
      q: "Which currency do I pay in?",
      a: "GBP, USD or EUR, by card. Your contractor and suppliers are paid in naira, at the exchange rate recorded on the day you fund. You see both amounts before you pay.",
    },
    {
      q: "Does iBackHome ever hold my money?",
      a: "No. Your funds go to a licensed escrow partner and are released only after the supervisor verifies the work and you approve it.",
    },
    {
      q: "Is the fee taken from my contractor’s payment?",
      a: "No. Fees are shown as separate lines when you fund a milestone. The milestone amount you agreed is what your contractor receives.",
    },
    ...(p.billing ? [{ q: "When is the monthly fee charged?", a: p.billing }] : []),
    ...(p.cancellation ? [{ q: "Can I stop at any time?", a: p.cancellation }] : []),
  ];

  return (
    <>
      <PricingHero
        title="A small price to protect what you value."
        lead="A monthly fee for supervision, a small fee each time you fund a milestone, and optional extras."
      >
        {priced ? null : (
          <Alert tone="info" title="Pricing is being finalised" className="max-w-3xl">
            Final prices are being set from our pilot. You always see every amount, and every fee, before you
            pay anything.
          </Alert>
        )}
      </PricingHero>
      <Section tone="mist" labelledBy="plans">
        <Reveal>
          <SectionHead
            centered
            id="plans"
            title="What you pay for"
            lead="Two simple parts: a monthly fee for supervision, and a small fee each time you fund a milestone."
          />
        </Reveal>
        <div className="grid gap-4 lg:grid-cols-2">
          <Reveal className="flex">
            <article className="flex w-full flex-col gap-4 rounded-card border border-line bg-white p-6 shadow-card">
              <p className="type-caption text-muted uppercase">Every project</p>
              <h3 className="type-h2 text-ink">Supervision subscription</h3>
              {priced ? (
                <p className="type-h3 text-ink">
                  {p.supervisionGbp} per project, per month
                  {p.supervisionUsd || p.supervisionEur ? (
                    <span className="type-small block font-normal text-slate">
                      Also in {[p.supervisionUsd, p.supervisionEur].filter(Boolean).join(" or ")}
                    </span>
                  ) : null}
                </p>
              ) : null}
              <CheckList
                items={[
                  "A vetted, registered supervisor for your site",
                  "Scheduled visits plus unannounced spot checks",
                  "Every photo and video checked: inside your site, device-signed, not reused",
                  "Milestone verification before any release",
                  "Weekly report, checked by your supervisor, on WhatsApp and email",
                  "Your dashboard: progress, evidence, spending and ledger",
                ]}
              />
            </article>
          </Reveal>
          <Reveal delay={150} className="flex">
            <article className="flex w-full flex-col gap-4 rounded-card border border-line bg-white p-6 shadow-card">
              <p className="type-caption text-muted uppercase">Each milestone</p>
              <h3 className="type-h2 text-ink">Funding fee</h3>
              {priced ? <p className="type-h3 text-ink">{p.fundingFee} of each milestone you fund</p> : null}
              <CheckList
                items={[
                  "Shown as its own line before you pay, never taken from your contractor",
                  "Release only after supervisor verification and your approval",
                  "Disputes pause the release until resolved",
                  "Your contractor is paid in naira at the recorded rate",
                  ...(p.escrowPartnerFee ? [`Escrow partner’s own fee: ${p.escrowPartnerFee}`] : []),
                ]}
              />
              <p className="type-small flex items-center gap-2 text-slate">
                <Lock aria-hidden strokeWidth={1.75} className="size-4" />
                Held by a licensed escrow partner, never by iBackHome.
              </p>
            </article>
          </Reveal>
        </div>
      </Section>
      <Section labelledBy="addons">
        <div className="grid items-start gap-8 lg:grid-cols-2 lg:gap-12">
          <div className="flex flex-col gap-8">
            <SectionHead
              id="addons"
              eyebrow="Optional"
              title="Add-ons"
              lead="Extras you can add to a project. Priced individually."
            />
            <ul className="grid gap-4">
              {[
                {
                  title: "Materials from verified suppliers",
                  body: "Order through partner suppliers; quotes are checked against our price index and delivery is confirmed on site.",
                  chip: <ToneChip label="Available" tone="ok" size="small" />,
                  price: p.materialsCharge,
                },
                {
                  title: "Extra live walkthroughs",
                  body: "A video call with your supervisor on site, booked in your time zone.",
                },
                { title: "Land and title verification", body: "Checks before you buy a plot." },
                { title: "Finishing supervision", body: "Closer supervision for interior finishing." },
              ].map((a, i) => (
                <li key={a.title} className="flex">
                  <Reveal delay={i * 120} className="flex w-full">
                    <div
                      className={
                        a.chip
                          ? "flex w-full flex-col gap-2 rounded-card border border-line bg-white p-5 shadow-card"
                          : "flex w-full flex-col gap-2 rounded-card border border-dashed border-line-strong bg-white p-5"
                      }
                    >
                      <p className="flex items-center justify-between gap-3">
                        <span className="type-h3 text-ink">{a.title}</span>
                        {a.chip ?? <ToneChip label="Coming soon" tone="neutral" size="small" />}
                      </p>
                      <p className="text-slate">{a.body}</p>
                      {a.price ? <p className="type-small font-semibold text-ink">{a.price}</p> : null}
                    </div>
                  </Reveal>
                </li>
              ))}
            </ul>
          </div>
          <Reveal
            delay={120}
            className="group overflow-hidden rounded-card shadow-raised lg:sticky lg:top-24 lg:order-first"
          >
            <Image
              src={PHOTOS.cementStack.src}
              alt={PHOTOS.cementStack.alt}
              width={PHOTOS.cementStack.width}
              height={PHOTOS.cementStack.height}
              sizes="(min-width: 1024px) 560px, 100vw"
              className="ibh-focus-50-72 aspect-4/5 w-full object-cover transition-transform duration-1000 ease-out group-hover:scale-105"
            />
          </Reveal>
        </div>
      </Section>
      <Section tone="mist" labelledBy="pricing-faq" className="max-w-3xl">
        <h2 id="pricing-faq" className="type-h1 text-ink">
          Pricing questions
        </h2>
        <Faq items={faq} />
      </Section>
      <p className="type-small mx-auto w-full max-w-336 px-4 pb-6 text-muted sm:px-8 lg:px-12 xl:px-16">
        Photography is illustrative: stock photography, not iBackHome customers or homes.
      </p>
      <CtaBand
        title="Start with your site and your contractor"
        secondary={{ label: "Ask about pricing", href: "/contact" }}
      />
    </>
  );
}
