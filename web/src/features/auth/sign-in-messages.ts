import type { UiState } from "@/common/api/errors";

// Copy from WEB-PUBLIC-010 (the AuthCard states) for the errors the backend really returns. The backend
// doesn't say how many attempts are left, so the design's "3 attempts left" line isn't shown (PACKAGE-REPORT).

export type Channel = "sms" | "whatsapp" | "email";

const CHANNEL_NAMES: Record<Channel, string> = { sms: "SMS", whatsapp: "WhatsApp", email: "email" };

export type Message = { title: string; detail: string };

function minutes(seconds: number | null): string {
  if (!seconds) return "a few minutes";
  const m = Math.ceil(seconds / 60);
  return m === 1 ? "1 minute" : `${m} minutes`;
}

export function signInMessage(state: UiState, channel: Channel): Message {
  const name = CHANNEL_NAMES[channel];
  switch (state.kind) {
    case "otp":
      if (state.problem === "otp_expired") {
        return { title: "This code has expired.", detail: "Codes last 5 minutes. Ask for a new one." };
      }
      if (state.problem === "too_many_attempts") {
        return { title: "Too many wrong attempts.", detail: "This code no longer works. Ask for a new one." };
      }
      return { title: "That code isn’t right.", detail: "Check the latest message and try again." };
    case "rate_limited":
      return {
        title: "Too many codes requested.",
        detail: `For your security, wait ${minutes(state.retryAfterSeconds)} before asking for another code for this number.`,
      };
    case "channel_unavailable":
      return {
        title: `${channel === "email" ? "Email" : name} codes aren’t available right now.`,
        detail:
          channel === "email"
            ? "Use your phone number instead."
            : `Choose ${channel === "sms" ? "WhatsApp" : "SMS"}, or switch to email.`,
      };
    case "send_failed":
      return {
        title: `We couldn’t send your code by ${name}.`,
        detail:
          channel === "email"
            ? "Try again, or use your phone number."
            : "Try again, or choose another way to get it.",
      };
    case "forbidden":
      return { title: "This account is suspended.", detail: "Contact us if you think this is a mistake." };
    case "validation":
      return {
        title: "Check the phone number or email.",
        detail: "Phone numbers outside Nigeria need the country code, for example +44.",
      };
    case "offline":
      return { title: "You're offline.", detail: "Check your connection and try again." };
    default:
      return {
        title: "Something went wrong on our side.",
        detail: "Nothing was charged, approved or released. Try again.",
      };
  }
}
