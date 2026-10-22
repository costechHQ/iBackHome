import { describe, expect, it } from "vitest";

import { signInMessage } from "./sign-in-messages";

describe("sign-in messages (WEB-PUBLIC-010 copy)", () => {
  it("uses the designed copy for each login-code problem", () => {
    expect(signInMessage({ kind: "otp", problem: "invalid_code" }, "sms").title).toBe(
      "That code isn’t right.",
    );
    expect(signInMessage({ kind: "otp", problem: "otp_expired" }, "sms").detail).toBe(
      "Codes last 5 minutes. Ask for a new one.",
    );
    expect(signInMessage({ kind: "otp", problem: "too_many_attempts" }, "sms").title).toBe(
      "Too many wrong attempts.",
    );
  });

  it("says how long to wait from the backend's Retry-After", () => {
    expect(signInMessage({ kind: "rate_limited", retryAfterSeconds: 540 }, "sms").detail).toContain(
      "wait 9 minutes",
    );
    expect(signInMessage({ kind: "rate_limited", retryAfterSeconds: null }, "sms").detail).toContain(
      "a few minutes",
    );
  });

  it("names the channel that is down and offers another, never switching silently", () => {
    expect(signInMessage({ kind: "channel_unavailable" }, "whatsapp")).toEqual({
      title: "WhatsApp codes aren’t available right now.",
      detail: "Choose SMS, or switch to email.",
    });
    expect(signInMessage({ kind: "send_failed" }, "sms").title).toBe("We couldn’t send your code by SMS.");
  });
});
