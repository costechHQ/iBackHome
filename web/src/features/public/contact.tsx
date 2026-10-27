import {
  ArrowRight,
  ClipboardCheck,
  Clock,
  HardHat,
  House,
  LogIn,
  Mail,
  MapPin,
  MessageCircle,
} from "lucide-react";
import Image from "next/image";
import Link from "next/link";
import type { ReactNode } from "react";

import { Button } from "@/common/ui/button";

import { Section, SectionHead } from "./blocks";
import { ContactHero } from "./contact-visuals";
import { PHOTOS } from "./photos";
import { Reveal } from "./reveal";
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
          value: company.officeAddress,
          note: "Visits by appointment",
        }
      : null,
    contact.openingHours
      ? { icon: Clock, label: "Hours", value: `${contact.openingHours} WAT`, note: "Nigerian time (UTC+1)" }
      : null,
  ];
  return channels.filter((c): c is Channel => c !== null);
}

type Route = { icon: typeof Mail; title: string; body: string; href: string };

// Where each kind of visitor should go next. The wording follows the pages they lead to.
const ROUTES: readonly Route[] = [
  { icon: House, title: "Planning a build", body: "See how a milestone gets paid.", href: "/how-it-works" },
  {
    icon: HardHat,
    title: "I'm a contractor",
    body: "Do honest work. Get paid without the wait.",
    href: "/contractors",
  },
  {
    icon: ClipboardCheck,
    title: "I want to supervise",
    body: "Be the eyes on site for families abroad.",
    href: "/supervisors",
  },
  {
    icon: LogIn,
    title: "I'm already a client",
    body: "Raise anything about a milestone from your dashboard.",
    href: "/sign-in",
  },
];

export function Contact() {
  const channels = contactChannels();
  const reply = SITE.contact.responseTime;
  return (
    <>
      <ContactHero
        title="Talk to us"
        lead={`Questions about a build, joining as a contractor or supervisor, or partnering with us.${reply ? ` We'll get back to you within ${reply}.` : ""}`}
      />

      <Section labelledBy="routes">
        <Reveal>
          <SectionHead
            centered
            id="routes"
            eyebrow="Start here"
            title="What brings you here?"
            lead="Pick the closest match, or go straight to a channel below."
          />
        </Reveal>
        <ul className="grid gap-4 sm:grid-cols-2 lg:grid-cols-4">
          {ROUTES.map(({ icon: Icon, title, body, href }, i) => (
            <li key={title} className="flex">
              <Reveal delay={i * 120} className="flex w-full">
                <Link
                  href={href}
                  className="group flex w-full flex-col gap-3 rounded-card border border-line bg-white p-5 shadow-card transition duration-300 hover:-translate-y-1 hover:shadow-raised"
                >
                  <span className="flex size-12 items-center justify-center rounded-control bg-navy-900 text-white">
                    <Icon aria-hidden strokeWidth={1.75} className="size-6" />
                  </span>
                  <span className="type-h3 text-ink">{title}</span>
                  <span className="text-slate">{body}</span>
                  <span className="type-small mt-auto flex items-center gap-1 pt-2 font-semibold text-accent">
                    Go
                    <ArrowRight
                      aria-hidden
                      strokeWidth={1.75}
                      className="size-4 transition-transform duration-300 group-hover:translate-x-1"
                    />
                  </span>
                </Link>
              </Reveal>
            </li>
          ))}
        </ul>
      </Section>

      <section
        aria-labelledby="channels"
        className="ibh-on-navy relative isolate overflow-hidden bg-navy-900 text-navy-200"
      >
        <div aria-hidden className="absolute inset-0 -z-10">
          <Image
            src={PHOTOS.officeDocuments.src}
            alt=""
            width={PHOTOS.officeDocuments.width}
            height={PHOTOS.officeDocuments.height}
            sizes="100vw"
            className="size-full object-cover opacity-15"
          />
          <div className="ibh-float absolute -top-40 -left-32 size-136 rounded-full bg-accent/30 blur-3xl" />
          <div className="ibh-float absolute -right-24 bottom-0 size-112 rounded-full bg-navy-700 blur-3xl [--ibh-delay:2s]" />
        </div>
        <div className="mx-auto grid max-w-336 items-center gap-12 px-4 py-16 sm:px-8 lg:grid-cols-2 lg:gap-16 lg:px-12 lg:py-24 xl:px-16">
          <div className="flex flex-col gap-8">
            <Reveal>
              <SectionHead
                onDark
                id="channels"
                title="How to reach us"
                lead="Questions about a build, joining us, or partnering: pick whichever channel is easiest."
              />
            </Reveal>
            {channels.length === 0 ? (
              <Reveal delay={150}>
                <div
                  role="status"
                  className="flex items-start gap-4 rounded-card border border-navy-700 bg-navy-800 p-5"
                >
                  <span className="relative mt-1.5 flex size-3 shrink-0">
                    <span className="absolute inline-flex size-full rounded-full bg-ok-fg opacity-60 motion-safe:animate-ping" />
                    <span className="relative inline-flex size-3 rounded-full bg-ok-fg" />
                  </span>
                  <p className="flex flex-col gap-1">
                    <span className="font-semibold text-white">Our contact details are on their way</span>
                    <span className="text-navy-200">
                      We&apos;re setting up our WhatsApp line and email. Check back soon.
                    </span>
                  </p>
                </div>
              </Reveal>
            ) : (
              <dl className="grid gap-3 sm:grid-cols-2">
                {channels.map((c, i) => (
                  <Reveal key={c.label} delay={i * 120} className="flex">
                    <div className="group flex w-full items-start gap-4 rounded-card bg-white p-5 text-slate shadow-card transition duration-300 hover:-translate-y-1 hover:shadow-raised">
                      <span className="flex size-11 shrink-0 items-center justify-center rounded-control bg-navy-900 text-white transition-transform duration-300 group-hover:scale-110">
                        <c.icon aria-hidden strokeWidth={1.75} className="size-5" />
                      </span>
                      <div className="flex flex-col gap-0.5">
                        <dt className="type-caption text-muted uppercase">{c.label}</dt>
                        <dd className="type-h3 text-ink">{c.value}</dd>
                        <dd className="type-small text-slate">{c.note}</dd>
                      </div>
                    </div>
                  </Reveal>
                ))}
              </dl>
            )}
            {reply ? (
              <p className="type-small flex w-fit items-center gap-2 rounded-pill border border-navy-700 bg-navy-800 px-4 py-2 text-white">
                <Clock aria-hidden strokeWidth={1.75} className="size-4" />
                We&apos;ll get back to you within {reply}.
              </p>
            ) : null}
            <Reveal delay={250}>
              <div className="flex flex-col gap-4 border-t border-navy-700 pt-8">
                <h3 className="type-h2 text-white">Already a client?</h3>
                <p className="type-body-lg text-navy-200">
                  Raise anything about a milestone from your dashboard — a dispute there pauses the release
                  straight away.
                </p>
                <Button asChild size="lg" variant="white-on-navy" className="self-start">
                  <Link href="/sign-in">Sign in</Link>
                </Button>
                <p className="type-small text-navy-200">
                  Photography is illustrative: stock photography, not iBackHome staff or customers.
                </p>
              </div>
            </Reveal>
          </div>

          <Reveal delay={200} className="mx-auto w-full max-w-md">
            <figure
              aria-label="Illustration of a chat with the iBackHome team"
              className="ibh-float rounded-3xl flex flex-col gap-4 bg-white p-5 shadow-raised"
            >
              <div className="flex items-center gap-3 border-b border-line pb-4">
                <span className="flex size-10 items-center justify-center rounded-pill bg-navy-900 text-white">
                  <MessageCircle aria-hidden strokeWidth={1.75} className="size-5" />
                </span>
                <span className="flex flex-col">
                  <span className="font-semibold text-ink">iBackHome</span>
                  <span className="type-caption flex items-center gap-1 tracking-normal text-ok-fg">
                    <span className="size-2 rounded-full bg-ok-fg" />
                    Online
                  </span>
                </span>
              </div>
              <div className="flex min-h-56 flex-col gap-3">
                <p className="ibh-chat-a type-small rounded-2xl rounded-br-md ml-auto max-w-4/5 bg-navy-900 px-4 py-2.5 text-white">
                  Hello, I&apos;m planning a build back home.
                </p>
                <p
                  aria-hidden
                  className="ibh-typing rounded-2xl rounded-bl-md flex w-fit items-center gap-1 bg-mist px-4 py-3"
                >
                  <span className="ibh-dot size-2 rounded-full bg-slate" />
                  <span className="ibh-dot size-2 rounded-full bg-slate [--ibh-delay:150ms]" />
                  <span className="ibh-dot size-2 rounded-full bg-slate [--ibh-delay:300ms]" />
                </p>
                <p className="ibh-chat-b type-small rounded-2xl rounded-bl-md max-w-4/5 bg-mist px-4 py-2.5 text-ink">
                  Welcome. Tell us about your site and we&apos;ll take it from here.
                </p>
              </div>
              <figcaption className="type-caption tracking-normal text-muted">
                Illustration, not a real conversation.
              </figcaption>
            </figure>
          </Reveal>
        </div>
      </section>
    </>
  );
}
