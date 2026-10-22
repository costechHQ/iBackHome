import type { Metadata } from "next";

import { LegalPage } from "@/features/public/legal";

export const metadata: Metadata = { title: "Privacy policy · iBackHome" };

export default function Page() {
  return <LegalPage doc="privacy" />;
}
