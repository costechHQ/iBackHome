import type { NextRequest } from "next/server";

import { verifyOtp } from "@/common/auth/session";

export const dynamic = "force-dynamic";

export function POST(req: NextRequest) {
  return verifyOtp(req);
}
