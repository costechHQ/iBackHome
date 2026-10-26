"use client";

import { ChevronLeft, ChevronRight } from "lucide-react";
import Image from "next/image";
import { useRef } from "react";

import type { Photo } from "./photos";

export type Stage = { title: string; body: string; photo: Photo };

const ARROW =
  "flex size-11 items-center justify-center rounded-pill border border-frame bg-white text-ink hover:bg-mist";

// A row of building stages the visitor swipes, scrolls or steps through with the arrows. Native scroll-snap, so
// it works with touch, trackpad and keyboard (the strip is focusable) and needs no timers.
export function StageScroller({ stages }: { stages: readonly Stage[] }) {
  const strip = useRef<HTMLUListElement>(null);

  const step = (direction: 1 | -1) => {
    const el = strip.current;
    if (!el) return;
    const card = el.firstElementChild as HTMLElement | null;
    const width = (card?.offsetWidth ?? el.clientWidth) + 16;
    el.scrollBy({ left: direction * width, behavior: "smooth" });
  };

  return (
    <div className="flex flex-col gap-4">
      <ul
        ref={strip}
        tabIndex={0}
        aria-label="Building stages, scroll sideways"
        className="ibh-scrollbar-none -mx-4 flex snap-x snap-mandatory scroll-px-4 gap-4 overflow-x-auto scroll-smooth px-4 pb-2 sm:-mx-8 sm:scroll-px-8 sm:px-8"
      >
        {stages.map(({ title, body, photo }, i) => (
          <li
            key={title}
            className="group relative aspect-4/5 w-64 shrink-0 snap-start overflow-hidden rounded-card bg-navy-900 shadow-card sm:w-72"
          >
            <Image
              src={photo.src}
              alt={photo.alt}
              width={photo.width}
              height={photo.height}
              sizes="288px"
              className="size-full object-cover transition-transform duration-700 ease-out group-hover:scale-105"
            />
            <div className="absolute inset-0 bg-linear-to-t from-navy-900/95 via-navy-900/30 to-transparent" />
            <div className="absolute inset-x-0 bottom-0 flex flex-col gap-1 p-4 text-white">
              <span className="type-caption tracking-normal text-navy-200 uppercase">Stage {i + 1}</span>
              <h3 className="type-h3">{title}</h3>
              <p className="type-small text-navy-200">{body}</p>
            </div>
          </li>
        ))}
      </ul>
      <div className="flex gap-2 self-end">
        <button type="button" aria-label="Earlier stages" onClick={() => step(-1)} className={ARROW}>
          <ChevronLeft aria-hidden strokeWidth={1.75} className="size-5" />
        </button>
        <button type="button" aria-label="Later stages" onClick={() => step(1)} className={ARROW}>
          <ChevronRight aria-hidden strokeWidth={1.75} className="size-5" />
        </button>
      </div>
    </div>
  );
}
