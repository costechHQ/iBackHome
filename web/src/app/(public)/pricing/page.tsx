import type { Metadata } from "next";

import { Pricing } from "@/features/public/pricing";

export const metadata: Metadata = {
  title: "Pricing · iBackHome",
  description:
    "A monthly fee for supervision, a small fee each time you fund a milestone, and optional extras.",
};

export default function Page() {
  return <Pricing />;
}
