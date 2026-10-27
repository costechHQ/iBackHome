import { FileCheck2, KeyRound, Lock } from "lucide-react";
import type { ReactNode } from "react";

import { BleedHero, type Stage } from "./bleed-hero";
import { PHOTOS } from "./photos";

// The trust page's hero (WEB-PUBLIC-006): the highest note of each currency a family might fund from or build in,
// as the banner's background. They fade into one another in turn, five seconds each (with reduced motion the last
// one stays), with the three escrow facts along the bottom. The wording uses no sample names or amounts
// (PACKAGE-REPORT W-37).

const NOTES: readonly [Stage, Stage, Stage, Stage] = [
  { photo: PHOTOS.noteNgn1000, label: "Nigeria ₦1,000" },
  { photo: PHOTOS.noteUsd100, label: "US $100" },
  { photo: PHOTOS.noteGbp50, label: "UK £50" },
  { photo: PHOTOS.noteEur500, label: "Euro €500" },
];

export function TrustHero({ title, lead, children }: { title: string; lead: string; children?: ReactNode }) {
  return (
    <BleedHero
      eyebrow="Trust and safety"
      title={title}
      lead={lead}
      stages={NOTES}
      facts={[
        { icon: Lock, title: "Your money is never ours", body: "A licensed escrow partner holds it." },
        { icon: KeyRound, title: "Two keys to release", body: "A verified milestone and your approval." },
        { icon: FileCheck2, title: "Every step on record", body: "A log that can't be edited." },
      ]}
    >
      {children}
      <p className="type-caption mt-4 max-w-2xl tracking-normal text-navy-200">
        Note photos: Koutchika Lihouenou Gaspard (₦1,000, CC BY-SA 4.0) and Vintage Fan 5678 (£50, CC BY 4.0),
        via Wikimedia Commons.
      </p>
    </BleedHero>
  );
}
