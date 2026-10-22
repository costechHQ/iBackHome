import createClient from "openapi-fetch";
import { describe, expect, it } from "vitest";

import { call } from "./client";
import { ApiError } from "./errors";
import type { paths } from "./schema";

// call() must keep the backend's error code even though openapi-fetch has already read the response body.

function answering(status: number, body: unknown, headers: Record<string, string> = {}) {
  return createClient<paths>({
    baseUrl: "http://test.invalid",
    fetch: async () =>
      new Response(JSON.stringify(body), {
        status,
        headers: { "content-type": "application/json", ...headers },
      }),
  });
}

describe("call()", () => {
  it("keeps the backend's code and message on an error", async () => {
    const api = answering(409, {
      error: { code: "second_approval_required", message: "A different ops user…" },
    });
    const error = await call(
      api.POST("/api/v1/disputes/{dispute_id}/resolve", {
        params: { path: { dispute_id: "d" } },
        body: { outcome: "release", notes: "x" },
      }),
    ).catch((e: unknown) => e);
    expect(error).toBeInstanceOf(ApiError);
    expect(error).toMatchObject({ status: 409, code: "second_approval_required" });
  });

  it("keeps 5xx codes the screens rely on, and Retry-After", async () => {
    const unavailable = await call(
      answering(503, { error: { code: "notifications_not_configured", message: "x" } }).POST(
        "/api/v1/auth/otp/request",
        { body: { identifier: "+447911123456", channel: "whatsapp" } },
      ),
    ).catch((e: unknown) => e);
    expect(unavailable).toMatchObject({ status: 503, code: "notifications_not_configured" });

    const limited = await call(
      answering(429, { error: { code: "rate_limited", message: "x" } }, { "retry-after": "60" }).POST(
        "/api/v1/auth/otp/request",
        { body: { identifier: "+447911123456" } },
      ),
    ).catch((e: unknown) => e);
    expect(limited).toMatchObject({ status: 429, code: "rate_limited", retryAfterSeconds: 60 });
  });

  it("returns the data on success", async () => {
    const data = await call(
      answering(202, { status: "sent", expires_in: 300 }).POST("/api/v1/auth/otp/request", {
        body: { identifier: "a@example.com", channel: "email" },
      }),
    );
    expect(data).toEqual({ status: "sent", expires_in: 300 });
  });
});
