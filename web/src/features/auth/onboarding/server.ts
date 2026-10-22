import "server-only";

import { serverApi } from "@/common/api/server";

import { missingSteps, type Step } from "./steps";

// Server-side: the steps a signed-in person still has to do. For a contractor it also checks the payout
// account; if that check fails (Paystack or the API down), they aren't held up for it.

type Me = { role: string; full_name?: string | null; country?: string | null; consent_required?: boolean };

export async function onboardingFor(me: Me): Promise<Step[]> {
  let hasPayout: boolean | null = null;
  if (me.role === "contractor") {
    const api = await serverApi();
    const { response } = await api
      .GET("/api/v1/me/payout/recipient")
      .catch(() => ({ response: null as Response | null }));
    hasPayout = response?.ok ? true : response?.status === 404 ? false : null;
  }
  return missingSteps(me, hasPayout);
}
