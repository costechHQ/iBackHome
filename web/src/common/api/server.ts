import "server-only";

import { cookies } from "next/headers";
import createClient from "openapi-fetch";

import { apiBaseUrl } from "../auth/backend";
import { ACCESS_COOKIE } from "../auth/cookies";
import type { paths } from "./schema";

/**
 * The API client for server components and layouts: calls FastAPI directly with the access token from the
 * cookie. It never refreshes (server components can't set cookies); src/proxy.ts makes sure the token is
 * fresh before the page renders. Every call is uncached.
 */
export async function serverApi() {
  const token = (await cookies()).get(ACCESS_COOKIE)?.value;
  return createClient<paths>({
    baseUrl: apiBaseUrl(),
    cache: "no-store",
    headers: token ? { authorization: `Bearer ${token}` } : {},
  });
}
