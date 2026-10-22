import type { NextRequest } from "next/server";

import { goHome } from "@/common/auth/session";

export const dynamic = "force-dynamic";

export function GET(req: NextRequest) {
  return goHome(req);
}
