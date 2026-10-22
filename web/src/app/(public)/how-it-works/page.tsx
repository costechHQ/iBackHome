import type { Metadata } from "next";

import { HowItWorks } from "@/features/public/how-it-works";

export const metadata: Metadata = {
  title: "How it works · iBackHome",
  description:
    "How a milestone gets paid: your contractor claims it, a vetted supervisor verifies it, you approve, and a licensed escrow partner pays.",
};

export default function Page() {
  return <HowItWorks />;
}
