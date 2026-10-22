// The sign-in flow's pure parts (WEB-PUBLIC-010), shared by the screens and the tests: building the phone
// number the backend expects, masking it on the code step, and the countdown text.

import { COUNTRIES } from "@/common/countries";

/** Codes can be sent again after 30 s (design assumption; the backend allows 3 codes per 15 minutes). */
export const RESEND_AFTER_SECONDS = 30;

/**
 * The identifier for POST /auth/otp/request from the picked calling code and what was typed. A number typed
 * with its own "+" is used as it is; otherwise the national trunk 0 is dropped ("07700 900482" with +44 is
 * +447700900482, "0803 123 4567" with +234 is +2348031234567). The backend normalises and checks it.
 */
export function phoneIdentifier(dial: string, typed: string): string {
  const trimmed = typed.trim();
  if (trimmed.startsWith("+")) return `+${trimmed.replace(/\D/g, "")}`;
  const digits = trimmed.replace(/\D/g, "").replace(/^0+/, "");
  return `+${dial}${digits}`;
}

/** The calling code an E.164 number starts with (the longest one that matches). */
export function dialOf(e164: string): string | null {
  const digits = e164.replace(/^\+/, "");
  let best: string | null = null;
  for (const c of COUNTRIES)
    if (digits.startsWith(c.dial) && (!best || c.dial.length > best.length)) best = c.dial;
  return best;
}

/** "+447700900482" -> "+44 7700 ••• 482"; an email is shown as it is (it's the person's own). */
export function maskIdentifier(identifier: string): string {
  if (identifier.includes("@")) return identifier;
  const dial = dialOf(identifier);
  if (!dial) return identifier;
  const national = identifier.replace(/^\+/, "").slice(dial.length);
  if (national.length < 8) return identifier;
  return `+${dial} ${national.slice(0, 4)} ••• ${national.slice(-3)}`;
}

/** 272 -> "4:32"; never negative. */
export function clock(seconds: number): string {
  const s = Math.max(0, Math.ceil(seconds));
  return `${Math.floor(s / 60)}:${String(s % 60).padStart(2, "0")}`;
}

/** Seconds left until `at` (epoch ms), never below 0. */
export function secondsUntil(at: number | null, now: number): number {
  return at === null ? 0 : Math.max(0, (at - now) / 1000);
}
