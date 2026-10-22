import type { NextRequest } from "next/server";

import { signOut } from "@/common/auth/session";

export const dynamic = "force-dynamic";

export function POST(req: NextRequest) {
  return signOut(req);
}
