import type { NextRequest } from "next/server";

import { refreshAndReturn } from "@/common/auth/session";

export const dynamic = "force-dynamic";

export function GET(req: NextRequest) {
  return refreshAndReturn(req);
}
