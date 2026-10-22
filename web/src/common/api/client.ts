"use client";

import createClient from "openapi-fetch";

import { apiErrorFrom, NetworkError } from "./errors";
import type { paths } from "./schema";

// The browser's API client, generated from the backend's OpenAPI (schema.d.ts). It calls our own origin:
// /api/v1/* is the auth proxy (ADR 0004), which adds the bearer token from the httpOnly cookie.

export const SESSION_EXPIRED_EVENT = "ibh:session-expired";

let client: ReturnType<typeof createClient<paths>> | null = null;

export function api() {
  client ??= createClient<paths>({
    baseUrl: window.location.origin,
    credentials: "same-origin",
    cache: "no-store",
  });
  return client;
}

/**
 * Unwraps an openapi-fetch call: returns `data`, or throws ApiError (with the backend's code) or NetworkError.
 * A 401 also tells the app shell to show the session-expired dialog.
 */
export async function call<T>(
  request: Promise<{ data?: T; error?: unknown; response: Response }>,
): Promise<T> {
  let result: Awaited<typeof request>;
  try {
    result = await request;
  } catch (cause) {
    throw new NetworkError(cause);
  }
  if (!result.response.ok) {
    const error = await apiErrorFrom(result.response);
    if (error.status === 401) window.dispatchEvent(new CustomEvent(SESSION_EXPIRED_EVENT));
    throw error;
  }
  return result.data as T;
}
