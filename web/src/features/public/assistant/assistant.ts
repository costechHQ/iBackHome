import { ApiError, NetworkError } from "@/common/api/errors";

import { SITE } from "../site";

// The website chat box (ADR 0006): the suggestions, the plain-language errors and where to send a person who
// needs a human. The answers come from the backend and are always vetted text; nothing typed is stored.

export const MAX_QUESTION = 500;

/** Give up on a slow answer after this long, so the visitor is never left waiting on a dot. */
export const ANSWER_TIMEOUT_MS = 15_000;

export const SUGGESTIONS = [
  "How does escrow work?",
  "How much does it cost?",
  "Can you find me a contractor?",
  "How do I become a supervisor?",
] as const;

export const DISCLAIMER =
  "Automated assistant. It answers common questions from our own text and can be wrong. Please don’t share passwords, your NIN or bank details.";

export type Role = "user" | "assistant";

export type ChatMessage = {
  id: number;
  role: Role;
  text: string;
  /** Other questions on the same topic (assistant messages only). */
  related?: readonly string[];
  /** The assistant is pointing the visitor to a person: show the contact buttons. */
  handoff?: boolean;
};

/** wa.me wants the number as digits only. */
export function whatsappHref(number: string): string {
  return `https://wa.me/${number.replace(/\D/g, "")}`;
}

export type ContactLink = { label: string; href: string; external: boolean };

/** Ways to reach a person, from the site's own contact details. The Contact page is always offered. */
export function contactLinks(contact = SITE.contact): ContactLink[] {
  const links: ContactLink[] = [];
  if (contact.whatsapp) {
    links.push({ label: "WhatsApp us", href: whatsappHref(contact.whatsapp), external: true });
  }
  if (contact.email) links.push({ label: "Email us", href: `mailto:${contact.email}`, external: true });
  links.push({ label: "Contact page", href: "/contact", external: false });
  return links;
}

/** True when the request was cut off by our own timeout (the browser reports TimeoutError or AbortError). */
export function timedOut(error: unknown): boolean {
  const cause: unknown = error instanceof NetworkError ? error.cause : error;
  const name = typeof cause === "object" && cause !== null ? (cause as { name?: unknown }).name : undefined;
  return name === "TimeoutError" || name === "AbortError";
}

/** The same question typed in a different case or with extra spaces is the same question (answers are cached). */
export function cacheKey(question: string): string {
  return question.trim().replace(/\s+/g, " ").toLowerCase();
}

/** What to tell the visitor when the assistant couldn't answer. Never shows a raw backend message. */
export function describeAssistantError(error: unknown): string {
  if (timedOut(error)) return "That is taking too long. Please try again, or contact us.";
  if (error instanceof NetworkError) {
    return "You seem to be offline. Check your connection and try again.";
  }
  if (error instanceof ApiError) {
    if (error.status === 429) {
      const minutes = error.retryAfterSeconds ? Math.ceil(error.retryAfterSeconds / 60) : null;
      return `You have asked a lot of questions. Please try again ${minutes ? `in about ${minutes} minute${minutes === 1 ? "" : "s"}` : "a little later"}, or contact us.`;
    }
    if (error.status === 503) return "The assistant isn’t available right now. Please contact us instead.";
    if (error.status === 422) return "I couldn’t read that. Please ask in a sentence or two.";
  }
  return "Something went wrong and I couldn’t answer. Please try again, or contact us.";
}

/** Worth offering "Try again": a slow or dropped request, not a refusal that would only repeat. */
export function retryable(error: unknown): boolean {
  if (timedOut(error) || error instanceof NetworkError) return true;
  return error instanceof ApiError && error.status >= 500 && error.status !== 503;
}

/** True when the question is worth sending (the backend needs at least two characters). */
export function askable(text: string): boolean {
  const trimmed = text.trim();
  return trimmed.length >= 2 && trimmed.length <= MAX_QUESTION;
}
