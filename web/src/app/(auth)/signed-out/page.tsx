import type { Metadata } from "next";

import { SignedOut } from "@/features/auth/auth-layout";

export const metadata: Metadata = { title: "Signed out · iBackHome" };

// WEB-OPS-001 "Signed out" (used by every portal).
export default function SignedOutPage() {
  return <SignedOut />;
}
