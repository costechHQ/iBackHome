import type { Metadata } from "next";

import { TrustAndSafety } from "@/features/public/trust";

export const metadata: Metadata = {
  title: "Trust and safety · iBackHome",
  description:
    "Who holds your money, how supervisors are vetted, why evidence can't be faked, and how your data is handled.",
};

export default function Page() {
  return <TrustAndSafety />;
}
