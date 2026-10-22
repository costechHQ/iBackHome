import { Camera, Images, KeyRound, MapPin } from "lucide-react";
import Link from "next/link";

import { Button } from "@/common/ui/button";

import { FeatureCards, PageHero, Section, SectionHead, Steps } from "./blocks";
import { SITE } from "./site";

// WEB-PUBLIC-006 Trust and safety. Every statement here is something the product does today (escrow through a
// partner, nightly reconciliation, two ops approvals, the evidence checks, AI that can't move money, 15-minute
// links, an audit log that can't be edited). The partner, regulator, data protection officer and contact
// details appear once site.ts has them (PACKAGE-REPORT W-37).

const SECTIONS = [
  ["escrow", "Escrow"],
  ["supervisors", "Supervisors"],
  ["evidence", "Evidence"],
  ["ai", "AI"],
  ["data", "Your data"],
  ["concern", "Report a concern"],
] as const;

export function TrustAndSafety() {
  const t = SITE.trust;
  return (
    <>
      <PageHero
        eyebrow="Trust and safety"
        title="How we protect your money, your site and your data"
        lead="Trust is the product. Here's exactly who holds your money, how supervisors are vetted, why evidence can't be faked, and how your data is handled under Nigerian law."
      >
        <nav aria-label="On this page">
          <ul className="flex flex-wrap gap-2">
            {SECTIONS.map(([id, label]) => (
              <li key={id}>
                <a
                  href={`#${id}`}
                  className="type-small flex min-h-target items-center rounded-pill border border-line px-3 text-ink hover:bg-mist"
                >
                  {label}
                </a>
              </li>
            ))}
          </ul>
        </nav>
      </PageHero>
      <Section tone="mist" labelledBy="escrow">
        <SectionHead
          id="escrow"
          title="Your money is never ours"
          lead="Client funds are held by a licensed escrow partner from the moment you pay until a milestone is released. iBackHome never holds client money."
        />
        {t.escrowPartner ? (
          <p className="rounded-card border border-line bg-white p-4 text-ink">
            <span className="font-semibold">Escrow partner: {t.escrowPartner}</span>
            {t.regulator ? ` · licensed by ${t.regulator}` : ""}
            {t.licenceNumber ? ` · licence ${t.licenceNumber}` : ""}
          </p>
        ) : null}
        <Steps
          items={[
            {
              title: "You pay by card",
              body: "In GBP, USD or EUR, through Stripe. Fees are shown before you pay.",
            },
            {
              title: "Escrow holds it",
              body: "Converted to naira at a recorded rate and held by the escrow partner.",
            },
            {
              title: "Two keys to release",
              body: "Supervisor verification and your approval. Either missing, nothing moves.",
            },
            {
              title: "Paid out directly",
              body: "The escrow partner pays your contractor or supplier in naira.",
            },
          ]}
        />
        <ul className="flex list-disc flex-col gap-2 pl-5 text-slate">
          <li>
            Every movement is recorded in a double-entry ledger you can view in your dashboard, with the
            exchange rate used.
          </li>
          <li>
            Our records are checked against the payment providers and the escrow partner every night;
            differences go straight to our team.
          </li>
          <li>
            A dispute pauses any release on that milestone until it&apos;s resolved, and resolving one needs
            sign-off from two of our staff.
          </li>
        </ul>
      </Section>
      <Section labelledBy="supervisors">
        <SectionHead
          id="supervisors"
          title="Supervisors are vetted, rotated and checked"
          lead="Supervisors are registered builders and engineers. Nobody is assigned to a site until our team has confirmed every check."
        />
        <FeatureCards
          columns={4}
          items={[
            { title: "Professional registration", body: "Verified with the relevant professional body." },
            { title: "Identity and guarantors", body: "A valid NIN and two guarantors we contact." },
            {
              title: "No relatives’ projects",
              body: "Supervisors declare relatives; they’re never assigned to or spot-check those contractors.",
            },
            {
              title: "Rotation and spot checks",
              body: "Rotated after two consecutive milestones, and checked by other supervisors unannounced.",
            },
          ]}
        />
      </Section>
      <Section tone="mist" labelledBy="evidence">
        <SectionHead
          id="evidence"
          title="Evidence that can’t be faked or reused"
          lead="Every photo and video passes the same checks before anyone treats it as proof. A failed check is logged and the capture never counts."
        />
        <FeatureCards
          columns={4}
          items={[
            {
              icon: Camera,
              title: "In-app camera only",
              body: "No gallery or file upload anywhere in the app.",
            },
            {
              icon: KeyRound,
              title: "Signed by a registered phone",
              body: "Each capture is signed on the device with a key that never leaves it.",
            },
            {
              icon: MapPin,
              title: "Inside the site, at the right time",
              body: "Rejected if taken outside the site boundary or if the phone’s clock has been changed.",
            },
            {
              icon: Images,
              title: "Compared with every photo",
              body: "Look-alikes from any project are flagged for our team to review.",
            },
          ]}
        />
      </Section>
      <Section labelledBy="ai">
        <SectionHead
          id="ai"
          title="AI that drafts and checks — and nothing more"
          lead="We use AI to write weekly reports, check quotes and flag suspicious photos. It’s labelled wherever it appears, and people make every decision."
        />
        <FeatureCards
          columns={4}
          items={[
            {
              title: "Can’t move money",
              body: "No AI can approve a milestone, release escrow or pay a supplier.",
            },
            {
              title: "Numbers from the ledger",
              body: "Money figures in reports come from payment records, never from the AI.",
            },
            { title: "Shows its sources", body: "Reports link to the exact photos they describe." },
            {
              title: "Reviewed and logged",
              body: "Your supervisor reviews each report before it’s sent; every AI run is recorded.",
            },
          ]}
        />
      </Section>
      <Section tone="mist" labelledBy="data">
        <SectionHead
          id="data"
          title="Your data, under the Nigeria Data Protection Act"
          lead="We handle personal data in line with the Nigeria Data Protection Act 2023. We ask for your consent when you sign up, collect only what the service needs, and log who accesses it."
        />
        <FeatureCards
          columns={3}
          items={[
            {
              title: "Consent first",
              body: "We ask for your consent at sign-up and explain what each piece of data is for.",
            },
            {
              title: "Only what’s needed",
              body: "We collect the minimum to run your project. Location details are removed from the photo files clients see.",
            },
            {
              title: "Private by default",
              body: "Site photos and videos are never public. Viewing links expire after 15 minutes.",
            },
            {
              title: "Access is logged",
              body: "Sensitive actions are written to a log that can’t be edited.",
            },
            {
              title: "Your rights",
              body: "Ask to see, correct or delete your data, or withdraw consent, by contacting us.",
            },
            ...(t.hostingAndRetention ? [{ title: "Where it’s stored", body: t.hostingAndRetention }] : []),
          ]}
        />
        <p className="flex flex-wrap gap-x-6 gap-y-2">
          <Link href="/privacy" className="font-semibold text-accent underline">
            Read the privacy policy
          </Link>
          {t.dpoName && t.dpoEmail ? (
            <span className="text-slate">
              Data protection officer: {t.dpoName} · {t.dpoEmail}
            </span>
          ) : null}
        </p>
      </Section>
      <Section labelledBy="concern" className="max-w-3xl">
        <SectionHead
          id="concern"
          title="Report a concern"
          lead="About a milestone? Raise a dispute from the milestone itself — it pauses the release. About a supervisor, a payment or your data? Contact our team directly."
        />
        <div className="flex flex-wrap items-center gap-4">
          <Button asChild size="lg">
            <Link href="/contact">Contact our team</Link>
          </Button>
          {t.trustEmail ? <span className="text-ink">{t.trustEmail}</span> : null}
        </div>
      </Section>
    </>
  );
}
