import type { Metadata } from "next";

import { ForContractors } from "@/features/public/audiences";

export const metadata: Metadata = {
  title: "For contractors · iBackHome",
  description:
    "Do honest work and get paid without the wait: verified milestones, payment in naira from the escrow partner.",
};

export default function Page() {
  return <ForContractors />;
}
