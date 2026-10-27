import { Banknote, Hammer, ShieldCheck, Smartphone } from "lucide-react";

import { BleedHero } from "./bleed-hero";
import { PHOTOS } from "./photos";

// The how-it-works page's hero (WEB-PUBLIC-002): a build cross-fading from walls going up to the finished home,
// with the four people in a payment. Photography is free-licence stock, and the page says so (PACKAGE-REPORT W-37).

export function HowHero({ title, lead }: { title: string; lead: string }) {
  return (
    <BleedHero
      eyebrow="How it works"
      title={title}
      lead={lead}
      stages={[
        { photo: PHOTOS.blockwork, label: "Walls going up" },
        { photo: PHOTOS.lagosApartments, label: "Structure rising" },
        { photo: PHOTOS.buildingGoldenHour, label: "Roof and slab" },
        { photo: PHOTOS.duplexDusk, label: "Finished home", focus: "ibh-focus-50-72" },
      ]}
      facts={[
        { icon: Hammer, title: "Your contractor builds", body: "And claims a finished stage." },
        { icon: ShieldCheck, title: "A supervisor checks", body: "On site, in the app." },
        { icon: Smartphone, title: "You decide", body: "From your phone." },
        { icon: Banknote, title: "Escrow pays", body: "Only when both say yes." },
      ]}
    />
  );
}
