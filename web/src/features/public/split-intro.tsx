import Image from "next/image";
import type { ReactNode } from "react";

import { cn } from "@/common/ui/cn";

import type { Photo } from "./photos";
import { Reveal } from "./reveal";

/** A section heading beside a photo that fades in and slowly zooms on hover. `flip` puts the photo on the left. */
export function SplitIntro({
  photo,
  focus,
  flip,
  children,
}: {
  photo: Photo;
  /** An `ibh-focus-*` class: where the photo is anchored when its frame crops it. */
  focus?: string;
  flip?: boolean;
  children: ReactNode;
}) {
  return (
    <div className="grid items-center gap-8 lg:grid-cols-2 lg:gap-12">
      <div className={cn("flex flex-col gap-4", flip && "lg:order-2")}>{children}</div>
      <Reveal delay={120} className="group overflow-hidden rounded-card shadow-raised">
        <Image
          src={photo.src}
          alt={photo.alt}
          width={photo.width}
          height={photo.height}
          sizes="(min-width: 1024px) 560px, 100vw"
          className={cn(
            "aspect-4/3 w-full object-cover transition-transform duration-1000 ease-out group-hover:scale-105",
            focus,
          )}
        />
      </Reveal>
    </div>
  );
}
