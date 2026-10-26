"use client";

import { ChevronLeft, ChevronRight, Pause, Play, ShieldCheck } from "lucide-react";
import Image from "next/image";
import { useCallback, useEffect, useRef, useState, useSyncExternalStore } from "react";

import { cn } from "@/common/ui/cn";

import { HERO_SLIDES } from "./photos";

const SLIDE_MS = 5500;
const SWIPE_PX = 40;

const REDUCED_MOTION = "(prefers-reduced-motion: reduce)";
const subscribeToMotion = (notify: () => void) => {
  const query = window.matchMedia(REDUCED_MOTION);
  query.addEventListener("change", notify);
  return () => query.removeEventListener("change", notify);
};
const prefersReducedMotion = () => window.matchMedia(REDUCED_MOTION).matches;

const ROUND_BUTTON =
  "flex size-9 items-center justify-center rounded-pill bg-navy-900 text-white hover:bg-navy-800";

// The landing hero's photo carousel: slow cross-fades with a gentle zoom, dots, arrows, swipe and arrow keys.
// It never moves for a visitor who prefers reduced motion, pauses while hovered, focused or hidden, and has
// a pause button (WCAG 2.2.2).
export function HeroCarousel() {
  const [index, setIndex] = useState(0);
  const [paused, setPaused] = useState(false); // chosen with the button
  const [engaged, setEngaged] = useState(false); // hovered or focused
  const [hidden, setHidden] = useState(false); // tab in the background
  const reduced = useSyncExternalStore(subscribeToMotion, prefersReducedMotion, () => false);
  const swipeStart = useRef<number | null>(null);

  const count = HERO_SLIDES.length;
  const go = useCallback((to: number) => setIndex((to + count) % count), [count]);
  const playing = !paused && !engaged && !hidden && !reduced;

  useEffect(() => {
    const onVisibility = () => setHidden(document.hidden);
    document.addEventListener("visibilitychange", onVisibility);
    return () => document.removeEventListener("visibilitychange", onVisibility);
  }, []);

  useEffect(() => {
    if (!playing) return;
    const timer = setTimeout(() => setIndex((i) => (i + 1) % count), SLIDE_MS);
    return () => clearTimeout(timer);
  }, [playing, index, count]);

  return (
    <div
      role="group"
      aria-roledescription="carousel"
      aria-label="Homes and building sites across Nigeria"
      className="relative isolate aspect-4/3 touch-pan-y overflow-hidden rounded-card bg-navy-900 shadow-raised select-none lg:aspect-square"
      onMouseEnter={() => setEngaged(true)}
      onMouseLeave={() => setEngaged(false)}
      onFocus={() => setEngaged(true)}
      onBlur={() => setEngaged(false)}
      onKeyDown={(event) => {
        if (event.key === "ArrowRight") go(index + 1);
        if (event.key === "ArrowLeft") go(index - 1);
      }}
      onPointerDown={(event) => {
        swipeStart.current = event.clientX;
      }}
      onPointerUp={(event) => {
        if (swipeStart.current === null) return;
        const moved = event.clientX - swipeStart.current;
        swipeStart.current = null;
        if (Math.abs(moved) >= SWIPE_PX) go(index + (moved < 0 ? 1 : -1));
      }}
    >
      {HERO_SLIDES.map(({ photo, line, position }, i) => (
        <div
          key={photo.src}
          role="group"
          aria-roledescription="slide"
          aria-label={`${i + 1} of ${count}`}
          aria-hidden={i !== index}
          className={cn(
            "absolute inset-0 transition-opacity duration-1000 ease-in-out",
            i === index ? "opacity-100" : "opacity-0",
          )}
        >
          <Image
            src={photo.src}
            alt={i === index ? photo.alt : ""}
            width={photo.width}
            height={photo.height}
            priority={i === 0}
            sizes="(min-width: 1024px) 900px, 100vw"
            className={cn("size-full object-cover", position, i === index && "ibh-kenburns")}
          />
          <div className="absolute inset-x-0 bottom-0 h-2/3 bg-linear-to-t from-navy-900/90 via-navy-900/40 to-transparent" />
          <p
            className={cn(
              "type-body-lg absolute right-4 bottom-16 left-4 font-semibold text-white transition-all duration-700 sm:right-20 sm:left-6",
              i === index ? "translate-y-0 opacity-100 delay-500" : "translate-y-3 opacity-0",
            )}
          >
            {line}
          </p>
        </div>
      ))}

      <p className="type-caption absolute top-4 left-4 flex items-center gap-1 rounded-pill bg-navy-900 px-3 py-1 tracking-normal text-white">
        <ShieldCheck aria-hidden strokeWidth={1.75} className="size-3.5" />
        Every site checked
      </p>

      <div className="ibh-on-navy absolute right-4 bottom-4 left-4 flex items-center justify-between gap-3 sm:left-6">
        <div className="flex items-center gap-1" role="group" aria-label="Choose a photo">
          {HERO_SLIDES.map(({ photo }, i) => (
            <button
              key={photo.src}
              type="button"
              aria-label={`Show photo ${i + 1}`}
              aria-current={i === index}
              onClick={() => go(i)}
              className="flex min-h-6 min-w-6 items-center justify-center"
            >
              <span
                className={cn(
                  "block h-1.5 rounded-pill transition-all duration-500",
                  i === index ? "w-8 bg-white" : "w-3 bg-navy-200",
                )}
              />
            </button>
          ))}
        </div>
        <div className="flex items-center gap-1">
          <button
            type="button"
            aria-label={paused ? "Play slideshow" : "Pause slideshow"}
            onClick={() => setPaused((value) => !value)}
            className={ROUND_BUTTON}
          >
            {paused ? (
              <Play aria-hidden strokeWidth={1.75} className="size-4" />
            ) : (
              <Pause aria-hidden strokeWidth={1.75} className="size-4" />
            )}
          </button>
          <button
            type="button"
            aria-label="Previous photo"
            onClick={() => go(index - 1)}
            className={ROUND_BUTTON}
          >
            <ChevronLeft aria-hidden strokeWidth={1.75} className="size-5" />
          </button>
          <button
            type="button"
            aria-label="Next photo"
            onClick={() => go(index + 1)}
            className={ROUND_BUTTON}
          >
            <ChevronRight aria-hidden strokeWidth={1.75} className="size-5" />
          </button>
        </div>
      </div>
    </div>
  );
}
