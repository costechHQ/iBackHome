import { ApiError, NetworkError } from "@/common/api/errors";

// Checks the public application forms share (/supervisors, /contractors). The backend repeats them and decides.

export const EMAIL = /^[^\s@]+@[^\s@]+\.[^\s@]+$/;
const PHONE_CHARS = /^\+?[0-9()\s-]+$/;

/** A problem with a phone number, saying whose it is ("your phone number"), or null when it looks fine. */
export function phoneProblem(raw: string, whose: string): string | null {
  const value = raw.trim();
  if (!value) return `Enter ${whose}`;
  const digits = value.replace(/\D/g, "");
  if (!PHONE_CHARS.test(value) || digits.length < 7 || digits.length > 15) {
    return `Enter a valid ${whose}, such as 0803 123 4567`;
  }
  return null;
}

export function emailProblem(raw: string): string | null {
  return EMAIL.test(raw.trim()) ? null : "Enter a valid email address";
}

/** At least two characters once trimmed; `what` completes "Enter ...". */
export function nameProblem(value: string, what: string): string | null {
  return value.trim().length < 2 ? `Enter ${what}` : null;
}

// What to tell the person when the backend (or the network) said no, for any application form. Never shows a
// raw backend message. `specific` maps a form's own error codes to a message and, where there is one, a field.

export type SubmitProblem<F extends string> = { message: string; field?: F };

export function describeApplyError<F extends string>(
  error: unknown,
  specific: Record<string, SubmitProblem<F>> = {},
): SubmitProblem<F> {
  if (error instanceof NetworkError) {
    return { message: "You seem to be offline. Check your connection and try again; nothing was sent." };
  }
  if (error instanceof ApiError) {
    if (error.status === 429) {
      const minutes = error.retryAfterSeconds ? Math.ceil(error.retryAfterSeconds / 60) : null;
      return {
        message: `Too many applications from this connection. Try again ${minutes ? `in about ${minutes} minute${minutes === 1 ? "" : "s"}` : "later"}.`,
      };
    }
    const own = specific[error.code];
    if (own) return own;
    if (error.code === "application_exists") {
      return {
        message:
          "We already have an application for this phone number or email. We’ll be in touch; there is no need to apply again.",
      };
    }
    if (error.code === "invalid_phone") {
      return { message: "One of the phone numbers isn’t valid. Check them and try again." };
    }
    if (error.status === 422)
      return { message: "Some answers weren’t accepted. Check the form and try again." };
  }
  return { message: "Something went wrong on our side and nothing was sent. Please try again in a moment." };
}
