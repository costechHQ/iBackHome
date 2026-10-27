import { Handshake, HardHat, House, Mail, MessageCircle } from "lucide-react";
import Image from "next/image";

import { Eyebrow } from "./blocks";
import { PHOTOS } from "./photos";

// The contact page's hero (WEB-PUBLIC-007): the headline and the three reasons to get in touch beside a phone
// that plays out a short chat. The chat is an illustration with generic wording and makes no promises about
// reply times or channels (PACKAGE-REPORT W-37). It plays once through every 16 seconds; with reduced motion
// every message shows still.

const REASONS = [
  { icon: House, label: "About a build" },
  { icon: HardHat, label: "Joining us" },
  { icon: Handshake, label: "Partnering" },
];

const BUBBLE = "type-small max-w-4/5 rounded-2xl px-4 py-2.5";

export function ContactHero({ title, lead }: { title: string; lead: string }) {
  const words = title.split(" ");
  return (
    <section className="ibh-on-navy relative isolate overflow-hidden bg-navy-900 text-navy-200">
      <div aria-hidden className="absolute inset-0 -z-10">
        <Image
          src={PHOTOS.supportTeam.src}
          alt=""
          width={PHOTOS.supportTeam.width}
          height={PHOTOS.supportTeam.height}
          priority
          sizes="100vw"
          className="size-full object-cover opacity-15"
        />
        <div className="ibh-float absolute -top-40 -left-32 size-136 rounded-full bg-accent/30 blur-3xl" />
        <div className="ibh-float absolute -right-24 -bottom-24 size-112 rounded-full bg-navy-700 blur-3xl [--ibh-delay:2s]" />
      </div>

      <div className="mx-auto grid max-w-336 items-center gap-14 px-4 py-16 sm:px-8 lg:grid-cols-2 lg:gap-8 lg:px-12 lg:py-24 xl:px-16">
        <div className="flex flex-col gap-6">
          <div className="ibh-rise self-start">
            <Eyebrow onDark>Contact</Eyebrow>
          </div>
          <h1 className="max-w-3xl text-5xl leading-none font-black tracking-tight text-white sm:text-6xl lg:text-7xl">
            {words.map((word, i) => (
              <span key={i} className="inline-block overflow-hidden pb-1 align-bottom">
                <span
                  className="ibh-word inline-block"
                  style={{ ["--ibh-delay" as string]: `${200 + i * 140}ms` }}
                >
                  {word}
                </span>
                {i < words.length - 1 ? " " : null}
              </span>
            ))}
          </h1>
          <p className="ibh-rise max-w-xl text-xl font-semibold text-navy-200 [--ibh-delay:300ms]">{lead}</p>
          <ul className="flex flex-wrap gap-3">
            {REASONS.map(({ icon: Icon, label }, i) => (
              <li
                key={label}
                className="ibh-rise type-small flex items-center gap-2 rounded-pill border border-navy-700 bg-navy-800 px-4 py-2 font-semibold text-white"
                style={{ ["--ibh-delay" as string]: `${500 + i * 150}ms` }}
              >
                <Icon aria-hidden strokeWidth={1.75} className="size-4" />
                {label}
              </li>
            ))}
          </ul>
        </div>

        <div className="ibh-rise relative mx-auto w-full max-w-sm [--ibh-delay:300ms]">
          <span
            aria-hidden
            className="ibh-float absolute -top-4 -left-6 z-10 hidden size-14 items-center justify-center rounded-pill bg-white text-navy-900 shadow-raised sm:flex"
          >
            <Mail strokeWidth={1.75} className="size-6" />
          </span>
          <span
            aria-hidden
            className="ibh-float absolute -right-5 bottom-24 z-10 hidden size-14 items-center justify-center rounded-pill bg-accent text-white shadow-raised [--ibh-delay:1.5s] sm:flex"
          >
            <MessageCircle strokeWidth={1.75} className="size-6" />
          </span>

          <figure
            aria-label="Illustration of a chat with the iBackHome team"
            className="rounded-3xl border-8 border-navy-700 bg-white p-4 shadow-raised"
          >
            <div className="mx-auto mb-3 h-1.5 w-16 rounded-pill bg-line" />
            <div className="flex items-center gap-3 border-b border-line pb-3">
              <span className="flex size-10 items-center justify-center rounded-pill bg-navy-900 text-white">
                <MessageCircle aria-hidden strokeWidth={1.75} className="size-5" />
              </span>
              <span className="font-semibold text-ink">iBackHome</span>
            </div>
            <div className="flex min-h-80 flex-col gap-3 py-4">
              <p className={`${BUBBLE} ibh-m1 rounded-br-md ml-auto bg-navy-900 text-white`}>
                Hello, I&apos;m planning a build back home.
              </p>
              <div className="grid">
                <p
                  aria-hidden
                  className="ibh-t1 rounded-2xl rounded-bl-md col-start-1 row-start-1 flex w-fit items-center gap-1 self-start bg-mist px-4 py-3"
                >
                  <span className="ibh-dot size-2 rounded-full bg-slate" />
                  <span className="ibh-dot size-2 rounded-full bg-slate [--ibh-delay:150ms]" />
                  <span className="ibh-dot size-2 rounded-full bg-slate [--ibh-delay:300ms]" />
                </p>
                <p className={`${BUBBLE} ibh-m2 rounded-bl-md col-start-1 row-start-1 bg-mist text-ink`}>
                  Welcome. Tell us about your site and we&apos;ll take it from here.
                </p>
              </div>
              <p className={`${BUBBLE} ibh-m3 rounded-br-md ml-auto bg-navy-900 text-white`}>
                I&apos;m also a contractor. Can I join?
              </p>
              <div className="grid">
                <p
                  aria-hidden
                  className="ibh-t2 rounded-2xl rounded-bl-md col-start-1 row-start-1 flex w-fit items-center gap-1 self-start bg-mist px-4 py-3"
                >
                  <span className="ibh-dot size-2 rounded-full bg-slate" />
                  <span className="ibh-dot size-2 rounded-full bg-slate [--ibh-delay:150ms]" />
                  <span className="ibh-dot size-2 rounded-full bg-slate [--ibh-delay:300ms]" />
                </p>
                <p className={`${BUBBLE} ibh-m4 rounded-bl-md col-start-1 row-start-1 bg-mist text-ink`}>
                  Yes. Contractors join through their client, and we&apos;ll show you how.
                </p>
              </div>
            </div>
            <figcaption className="type-caption tracking-normal text-muted">
              Illustration, not a real conversation.
            </figcaption>
          </figure>
        </div>
      </div>
    </section>
  );
}
