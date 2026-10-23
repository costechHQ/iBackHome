import type { Metadata } from "next";

import { BecomeASupervisor } from "@/features/public/audiences";

export const metadata: Metadata = {
  title: "Become a supervisor · iBackHome",
  description:
    "Registered builders and engineers across Nigeria: visit sites, capture evidence and verify each stage of work.",
};

export default function Page() {
  return <BecomeASupervisor />;
}
