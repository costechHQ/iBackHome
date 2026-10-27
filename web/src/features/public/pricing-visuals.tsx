import { CalendarCheck, Eye, PackagePlus, Receipt } from "lucide-react";
import type { ReactNode } from "react";

import { BleedHero } from "./bleed-hero";
import { PHOTOS } from "./photos";

// The pricing page's hero (WEB-PUBLIC-003): the kind of home you are protecting, with the four
// things you pay for. Photography is free-licence stock, and the page says so (PACKAGE-REPORT W-37).

export function PricingHero({
  title,
  lead,
  children,
}: {
  title: string;
  lead: string;
  children?: ReactNode;
}) {
  return (
    <BleedHero
      eyebrow="Pricing"
      title={title}
      lead={lead}
      main={PHOTOS.villaPoolPalms}
      facts={[
        { icon: CalendarCheck, title: "A monthly supervision fee", body: "Per project, per month." },
        { icon: Receipt, title: "A small funding fee", body: "Each time you fund a milestone." },
        { icon: PackagePlus, title: "Optional extras", body: "Materials and more." },
        { icon: Eye, title: "No surprises", body: "Every fee shown before you pay." },
      ]}
    >
      {children}
    </BleedHero>
  );
}
