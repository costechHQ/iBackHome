import "server-only";

import type { components } from "../api/schema";
import { serverApi } from "../api/server";
import type { Role } from "./roles";

export type Me = components["schemas"]["MeOut"];

export type Viewer = { status: "signed_out" } | { status: "forbidden"; me: Me } | { status: "ok"; me: Me };

/**
 * For route-group layouts: who is signed in, and may they see this portal? The backend still checks every
 * request; this only picks the right page. GET /me is read on every render, never cached.
 */
export async function viewerFor(allowed: readonly Role[]): Promise<Viewer> {
  const api = await serverApi();
  const { data, response } = await api.GET("/api/v1/me").catch(() => ({ data: undefined, response: null }));
  if (!response?.ok || !data) return { status: "signed_out" };
  if (data.status !== "active" || !allowed.includes(data.role as Role))
    return { status: "forbidden", me: data };
  return { status: "ok", me: data };
}
