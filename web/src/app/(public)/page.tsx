import type { Metadata } from "next";

import { Landing } from "@/features/public/landing";

export const metadata: Metadata = {
  title: "iBackHome · Far from home, never out of sight",
  description:
    "For Nigerians abroad building at home: verified supervisors capture site evidence, and a licensed escrow partner releases money milestone by milestone, only after you approve.",
};

export default function Page() {
  return <Landing />;
}
