import Image from "next/image";

import { cn } from "@/common/ui/cn";

import { SectionHead } from "./blocks";
import type { Photo } from "./photos";
import { Reveal } from "./reveal";

export type MarqueeItem = {
  photo: Photo;
  label: string;
  /** An `ibh-focus-*` class: where the photo is anchored when the card crops it. */
  focus?: string;
};

function MarqueeCard({ photo, label, focus, hidden }: MarqueeItem & { hidden?: boolean }) {
  return (
    <li
      aria-hidden={hidden}
      className="group relative h-72 w-64 shrink-0 overflow-hidden rounded-card shadow-card sm:h-80 sm:w-72"
    >
      <Image
        src={photo.src}
        alt={hidden ? "" : photo.alt}
        width={photo.width}
        height={photo.height}
        sizes="288px"
        className={cn(
          "size-full object-cover transition-transform duration-700 ease-out group-hover:scale-110",
          focus,
        )}
      />
      <div className="absolute inset-0 bg-linear-to-t from-navy-900/70 via-transparent to-transparent" />
      <span className="type-small absolute bottom-3 left-3 rounded-pill bg-white px-3 py-1 font-semibold text-ink">
        {label}
      </span>
    </li>
  );
}

/**
 * A slow, endless row of photo cards with a heading above it. The second copy is hidden from assistive tech;
 * it pauses on hover or focus, and with reduced motion the row scrolls by hand instead.
 */
export function PhotoMarquee({
  id,
  eyebrow,
  title,
  lead,
  items,
  note,
}: {
  id: string;
  eyebrow: string;
  title: string;
  lead: string;
  items: readonly MarqueeItem[];
  note: string;
}) {
  return (
    <section aria-labelledby={id} className="overflow-hidden bg-white py-14 lg:py-20">
      <div className="mx-auto mb-8 max-w-336 px-4 sm:px-8 lg:px-12 xl:px-16">
        <Reveal>
          <SectionHead id={id} eyebrow={eyebrow} title={title} lead={lead} />
        </Reveal>
      </div>
      <div className="ibh-marquee">
        <ul className="ibh-marquee-track flex w-max gap-4 pl-4">
          {items.map((item) => (
            <MarqueeCard key={item.label} {...item} />
          ))}
          {items.map((item) => (
            <MarqueeCard key={`${item.label}-copy`} {...item} hidden />
          ))}
        </ul>
      </div>
      <p className="type-small mx-auto mt-6 max-w-336 px-4 text-muted sm:px-8 lg:px-12 xl:px-16">{note}</p>
    </section>
  );
}
