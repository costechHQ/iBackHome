import type { NextRequest } from "next/server";

import { proxyToApi } from "@/common/api/proxy";

// The same-origin API proxy (ADR 0003). All logic is in common/api/proxy.ts.
export const dynamic = "force-dynamic";

type Context = { params: Promise<{ path: string[] }> };

const handle = async (req: NextRequest, { params }: Context) => proxyToApi(req, (await params).path);

export { handle as DELETE, handle as GET, handle as PATCH, handle as POST, handle as PUT };
