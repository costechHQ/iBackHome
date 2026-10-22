import { Clock, Mail, MapPin, MessageCircle } from "lucide-react";
import Link from "next/link";
import type { ReactNode } from "react";

import { Alert } from "@/common/ui/alert";

import { PageHero, Section } from "./blocks";
import { SITE, type SiteContent } from "./site";

// WEB-PUBLIC-007 Contact. There's no contact endpoint, so the design's form isn't built (PACKAGE-REPORT W-37):
// the page lists the channels from site.ts, and says they're on their way while none is set.

type Channel = { icon: typeof Mail; label: string; value: ReactNode; note: string };

/** wa.me wants the number as digits only. */
export function whatsappLink(number: string): string {
  return `https://wa.me/${number.replace(/\D/g, "")}`;
}

export function contactChannels(content: SiteContent = SITE): Channel[] {
  const { contact, company } = content;
  const channels: (Channel | null)[] = [
    contact.whatsapp
      ? {
          icon: MessageCircle,
          label: "WhatsApp",
          value: (
            <a href={whatsappLink(contact.whatsapp)} className="text-accent underline">
              {contact.whatsapp}
            </a>
          ),
          note: "Fastest for quick questions",
        }
      : null,
    contact.email
      ? {
          icon: Mail,
          label: "Email",
          value: (
            <a href={`mailto:${contact.email}`} className="text-accent underline">
              {contact.email}
            </a>
          ),
          note: "For anything with documents",
        }
      : null,
    company.officeAddress
      ? {
          icon: MapPin,
          label: "Office",
          value: `${company.officeAddress}, Enugu`,
          note: "Visits by appointment",
        }
      : null,
    contact.openingHours
      ? { icon: Clock, label: "Hours", value: `${contact.openingHours} WAT`, note: "Nigerian time (UTC+1)" }
      : null,
  ];
  return channels.filter((c): c is Channel => c !== null);
}

export function Contact() {
  const channels = contactChannels();
  const reply = SITE.contact.responseTime;
  return (
    <>
      <PageHero
        eyebrow="Contact"
        title="Talk to us"
        lead={`Questions about a build, joining as a contractor or supervisor, or partnering with us.${reply ? ` We'll get back to you within ${reply}.` : ""}`}
      />
      <Section tone="mist" labelledBy="channels" className="max-w-3xl">
        <h2 id="channels" className="type-h2 text-ink">
          How to reach us
        </h2>
        {channels.length === 0 ? (
          <Alert tone="info" title="Our contact details are on their way">
            We&apos;re setting up our WhatsApp line and email. Check back soon.
          </Alert>
        ) : (
          <dl className="grid gap-4 sm:grid-cols-2">
            {channels.map((c) => (
              <div
                key={c.label}
                className="flex gap-3 rounded-card border border-line bg-white p-5 shadow-card"
              >
                <c.icon aria-hidden strokeWidth={1.75} className="mt-1 size-5 flex-none text-accent" />
                <div className="flex flex-col gap-1">
                  <dt className="font-semibold text-ink">{c.label}</dt>
                  <dd className="text-ink">{c.value}</dd>
                  <dd className="type-small text-slate">{c.note}</dd>
                </div>
              </div>
            ))}
          </dl>
        )}
        <p className="text-slate">
          Already a client?{" "}
          <Link href="/sign-in" className="text-accent underline">
            Sign in
          </Link>{" "}
          and raise anything about a milestone from your dashboard — a dispute there pauses the release
          straight away.
        </p>
      </Section>
    </>
  );
}
