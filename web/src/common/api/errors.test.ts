import { describe, expect, it } from "vitest";

import { ApiError, apiErrorFrom, NetworkError, toUiState } from "./errors";
import { IdempotentAction } from "./idempotency";

const json = (status: number, body: unknown, headers: Record<string, string> = {}) =>
  new Response(JSON.stringify(body), { status, headers: { "content-type": "application/json", ...headers } });

describe("apiErrorFrom", () => {
  it("reads the backend's error shape, Retry-After and the request ID", async () => {
    const err = await apiErrorFrom(
      json(
        429,
        { error: { code: "rate_limited", message: "Too many login codes requested." } },
        { "retry-after": "540", "x-request-id": "req-1" },
      ),
    );
    expect(err).toMatchObject({
      status: 429,
      code: "rate_limited",
      retryAfterSeconds: 540,
      requestId: "req-1",
    });
  });

  it("falls back to the HTTP status when the body isn't ours", async () => {
    const err = await apiErrorFrom(new Response("<html>Bad gateway</html>", { status: 502 }));
    expect(err).toMatchObject({ status: 502, code: "server_error" });
  });
});

describe("toUiState (error-codes-to-ui.md)", () => {
  const ui = (status: number, code: string, retryAfter: number | null = null) =>
    toUiState(new ApiError(status, code, "x", retryAfter, "req-9"));

  it("treats every 409 as a designed conflict, never a crash", () => {
    expect(ui(409, "invalid_transition")).toEqual({ kind: "conflict", code: "invalid_transition" });
    expect(ui(409, "milestone_not_verified")).toEqual({ kind: "conflict", code: "milestone_not_verified" });
    expect(ui(409, "second_approval_required")).toEqual({
      kind: "conflict",
      code: "second_approval_required",
    });
  });

  it("maps the backend's real login-code errors", () => {
    expect(ui(400, "invalid_code")).toEqual({ kind: "otp", problem: "invalid_code" });
    expect(ui(400, "otp_expired")).toEqual({ kind: "otp", problem: "otp_expired" });
    expect(ui(429, "too_many_attempts")).toEqual({ kind: "otp", problem: "too_many_attempts" });
    expect(ui(429, "rate_limited", 600)).toEqual({ kind: "rate_limited", retryAfterSeconds: 600 });
    expect(ui(503, "notifications_not_configured")).toEqual({ kind: "channel_unavailable" });
    expect(ui(502, "notification_failed")).toEqual({ kind: "send_failed" });
  });

  it("maps the HTTP classes", () => {
    expect(ui(401, "session_expired")).toEqual({ kind: "session_expired" });
    expect(ui(403, "not_project_member")).toEqual({ kind: "forbidden", code: "not_project_member" });
    expect(ui(404, "not_found")).toEqual({ kind: "not_found" });
    expect(ui(422, "validation_error")).toEqual({ kind: "validation", code: "validation_error" });
    expect(ui(500, "internal_error")).toEqual({ kind: "server", requestId: "req-9" });
  });

  it("shows offline when the request never left", () => {
    expect(toUiState(new NetworkError())).toEqual({ kind: "offline" });
  });
});

describe("IdempotentAction", () => {
  let n = 0;
  const action = () => new IdempotentAction<{ notes: string }>(() => `key-${++n}`);

  it("reuses the key when the same action is retried", () => {
    const a = action();
    const first = a.keyFor({ notes: "ok" });
    expect(a.keyFor({ notes: "ok" })).toBe(first);
  });

  it("starts a new action when the input changes or after a success", () => {
    const a = action();
    const first = a.keyFor({ notes: "ok" });
    const changed = a.keyFor({ notes: "different" });
    expect(changed).not.toBe(first);
    a.done();
    expect(a.keyFor({ notes: "different" })).not.toBe(changed);
  });
});
