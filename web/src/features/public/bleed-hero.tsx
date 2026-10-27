import type { LucideIcon } from "lucide-react";
import Image from "next/image";
import type { ReactNode } from "react";

import { Eyebrow } from "./blocks";
import type { Photo } from "./photos";

// The full-bleed hero shared by the trust, how-it-works and pricing pages: a wide photo across two thirds of a
// dark banner, a second photo in the last third (large screens), the headline over a navy fade, and a row of
// short facts along the bottom. Everything rises in on load; the motion stops for visitors who ask for less.

export type Fact = { icon: LucideIcon; title: string; body: string };

/** One frame of a build that cross-fades into the next: the last one is the finished home. */
export type Stage = { photo: Photo; label: string; focus?: string };

const FACT_COLUMNS = { 3: "lg:grid-cols-3", 4: "lg:grid-cols-4" } as const;
const STAGE_DELAYS = ["0s", "5s", "10s", "15s"] as const;

export function BleedHero({
  eyebrow,
  title,
  lead,
  main,
  stages,
  side,
  sideFocus,
  facts,
  children,
}: {
  eyebrow: string;
  title: string;
  lead: string;
  /** One photo across the banner. Give this or `stages`. */
  main?: Photo;
  /**
   * Four photos that cross-fade in turn, from an unfinished build to the finished home, each with a label. With
   * reduced motion only the last one shows. Used instead of `main`, so there is no side photo.
   */
  stages?: readonly [Stage, Stage, Stage, Stage];
  /** A second photo in the last third on large screens; without it the main photo fills the banner. */
  side?: Photo;
  /** An `ibh-focus-*` class: where the side photo is anchored when its column crops it. */
  sideFocus?: string;
  facts: readonly [Fact, Fact, Fact] | readonly [Fact, Fact, Fact, Fact];
  children?: ReactNode;
}) {
  return (
    <section className="ibh-on-navy relative isolate overflow-hidden bg-navy-900 text-navy-200">
      <div aria-hidden className="absolute inset-0 -z-10 grid grid-cols-3">
        {stages ? (
          <div className="relative col-span-3 overflow-hidden">
            {stages.map(({ photo, focus }, i) => (
              <Image
                key={photo.src}
                src={photo.src}
                alt=""
                width={photo.width}
                height={photo.height}
                priority={i === 0}
                sizes="100vw"
                className={`ibh-stage absolute inset-0 size-full object-cover ${focus ?? ""}`}
                style={{ ["--ibh-delay" as string]: STAGE_DELAYS[i] }}
              />
            ))}
            <ul className="absolute top-4 right-4 sm:top-8 sm:right-8 lg:right-12 xl:right-16">
              {stages.map(({ label }, i) => (
                <li
                  key={label}
                  className="ibh-stage-label type-small absolute top-0 right-0 rounded-pill bg-white px-3 py-1 font-semibold whitespace-nowrap text-ink"
                  style={{ ["--ibh-delay" as string]: STAGE_DELAYS[i] }}
                >
                  {label}
                </li>
              ))}
            </ul>
          </div>
        ) : main ? (
          <div className={`relative col-span-3 overflow-hidden ${side ? "lg:col-span-2" : ""}`}>
            <Image
              src={main.src}
              alt=""
              width={main.width}
              height={main.height}
              priority
              sizes={side ? "(min-width: 1024px) 66vw, 100vw" : "100vw"}
              className="ibh-kenburns size-full object-cover"
            />
          </div>
        ) : null}
        {side ? (
          <div className="relative hidden overflow-hidden lg:block">
            <Image
              src={side.src}
              alt=""
              width={side.width}
              height={side.height}
              priority
              sizes="33vw"
              className={`size-full object-cover ${sideFocus ?? ""}`}
            />
          </div>
        ) : null}
        <div className="absolute inset-0 bg-linear-to-r from-navy-900 via-navy-900/80 to-navy-900/30" />
        <div className="absolute inset-x-0 bottom-0 h-1/2 bg-linear-to-t from-navy-900 to-transparent" />
      </div>

      <div className="mx-auto flex max-w-336 flex-col gap-6 px-4 pt-16 pb-12 sm:px-8 lg:px-12 lg:pt-24 xl:px-16">
        <div className="ibh-rise self-start">
          <Eyebrow onDark>{eyebrow}</Eyebrow>
        </div>
        <h1 className="type-display ibh-rise max-w-3xl text-white [--ibh-delay:120ms]">{title}</h1>
        <p className="type-body-lg ibh-rise max-w-2xl text-navy-200 [--ibh-delay:240ms]">{lead}</p>
        {children ? <div className="ibh-rise [--ibh-delay:360ms]">{children}</div> : null}
      </div>

      <ul
        className={`mx-auto grid max-w-336 gap-px border-t border-navy-700 px-4 sm:grid-cols-2 sm:px-8 lg:px-12 xl:px-16 ${FACT_COLUMNS[facts.length]}`}
      >
        {facts.map(({ icon: Icon, title: factTitle, body }, i) => (
          <li
            key={factTitle}
            className="ibh-rise flex items-center gap-4 py-5 lg:px-4 lg:first:pl-0"
            style={{ ["--ibh-delay" as string]: `${500 + i * 150}ms` }}
          >
            <span className="flex size-11 shrink-0 items-center justify-center rounded-control bg-navy-800 text-white">
              <Icon aria-hidden strokeWidth={1.75} className="size-5" />
            </span>
            <span className="flex flex-col">
              <span className="font-semibold text-white">{factTitle}</span>
              <span className="type-small text-navy-200">{body}</span>
            </span>
          </li>
        ))}
      </ul>
    </section>
  );
}
