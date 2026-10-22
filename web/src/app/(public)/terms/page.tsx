import type { Metadata } from "next";

import { LegalPage } from "@/features/public/legal";

export const metadata: Metadata = { title: "Terms of use · iBackHome" };

export default function Page() {
  return <LegalPage doc="terms" />;
}
