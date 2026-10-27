import { FileCheck2, KeyRound, Lock } from "lucide-react";
import type { ReactNode } from "react";

import { BleedHero } from "./bleed-hero";
import { PHOTOS } from "./photos";

// The trust page's hero (WEB-PUBLIC-006): naira notes, with the three escrow facts. Photography
// is free-licence stock, and the page says so. The wording uses no sample names or amounts (PACKAGE-REPORT W-37).

export function TrustHero({ title, lead, children }: { title: string; lead: string; children?: ReactNode }) {
  return (
    <BleedHero
      eyebrow="Trust and safety"
      title={title}
      lead={lead}
      main={PHOTOS.nairaNotesWide}
      facts={[
        { icon: Lock, title: "Your money is never ours", body: "A licensed escrow partner holds it." },
        { icon: KeyRound, title: "Two keys to release", body: "A verified milestone and your approval." },
        { icon: FileCheck2, title: "Every step on record", body: "A log that can't be edited." },
      ]}
    >
      {children}
    </BleedHero>
  );
}
