import { House } from "lucide-react";
import Image from "next/image";

import { PHOTOS, type Photo } from "./photos";

// The footer's call-to-action illustration: three rings turning slowly around the iBackHome home, each carrying
// a person's photo that stays upright as it goes round. Stock photography, so the people are illustrative. The
// rings stop turning for visitors who ask for less motion.

type Rider = { photo: Photo; seconds: number; offset: number };

const RINGS: readonly { inset: string; riders: readonly Rider[] }[] = [
  { inset: "inset-24", riders: [{ photo: PHOTOS.youngEngineer, seconds: 30, offset: 0 }] },
  {
    inset: "inset-12",
    riders: [
      { photo: PHOTOS.engineerPlans, seconds: 45, offset: 0 },
      { photo: PHOTOS.nairaPayout, seconds: 45, offset: 22 },
    ],
  },
  {
    inset: "inset-0",
    riders: [
      { photo: PHOTOS.headsetSmile, seconds: 60, offset: 0 },
      { photo: PHOTOS.engineerPhone, seconds: 60, offset: 30 },
    ],
  },
];

export function FooterOrbit() {
  return (
    <div aria-hidden className="relative mx-auto aspect-square w-full max-w-sm">
      {RINGS.map(({ inset, riders }) => (
        <div key={inset} className={`absolute rounded-full border border-line ${inset}`}>
          {riders.map(({ photo, seconds, offset }) => (
            <div
              key={photo.src}
              className="ibh-orbit absolute inset-0"
              style={{
                ["--ibh-dur" as string]: `${seconds}s`,
                ["--ibh-delay" as string]: `-${offset}s`,
              }}
            >
              <span className="absolute top-0 left-1/2 size-11 -translate-x-1/2 -translate-y-1/2">
                <span
                  className="ibh-orbit-rev block size-full overflow-hidden rounded-full shadow-card ring-4 ring-white"
                  style={{
                    ["--ibh-dur" as string]: `${seconds}s`,
                    ["--ibh-delay" as string]: `-${offset}s`,
                  }}
                >
                  <Image
                    src={photo.src}
                    alt=""
                    width={photo.width}
                    height={photo.height}
                    sizes="44px"
                    className="size-full object-cover object-top"
                  />
                </span>
              </span>
            </div>
          ))}
        </div>
      ))}
      <span className="absolute top-1/2 left-1/2 flex size-16 -translate-x-1/2 -translate-y-1/2 items-center justify-center rounded-full bg-navy-900 text-white shadow-raised">
        <House strokeWidth={1.75} className="size-7" />
      </span>
    </div>
  );
}
