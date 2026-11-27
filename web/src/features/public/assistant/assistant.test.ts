import { describe, expect, it } from "vitest";

import { ApiError, NetworkError } from "@/common/api/errors";

import {
  askable,
  contactLinks,
  describeAssistantError,
  MAX_QUESTION,
  SUGGESTIONS,
  whatsappHref,
} from "./assistant";

describe("contactLinks", () => {
  it("offers WhatsApp, email and the Contact page, in that order", () => {
    const links = contactLinks({
      email: "hello@ibackhome.com",
      whatsapp: "+234 803 836 2327",
      responseTime: null,
      openingHours: null,
    });
    expect(links.map((l) => l.label)).toEqual(["WhatsApp us", "Email us", "Contact page"]);
    expect(links[0]?.href).toBe("https://wa.me/2348038362327");
    expect(links[1]?.href).toBe("mailto:hello@ibackhome.com");
    expect(links[2]).toMatchObject({ href: "/contact", external: false });
  });

  it("always keeps the Contact page, even when the other details are missing", () => {
    const links = contactLinks({ email: null, whatsapp: null, responseTime: null, openingHours: null });
    expect(links.map((l) => l.label)).toEqual(["Contact page"]);
  });
});

describe("whatsappHref", () => {
  it("keeps the digits only", () => {
    expect(whatsappHref("+234 (803) 836-2327")).toBe("https://wa.me/2348038362327");
  });
});

describe("askable", () => {
  it("needs two characters and at most the backend's limit", () => {
    expect(askable("")).toBe(false);
    expect(askable(" a ")).toBe(false);
    expect(askable("hi")).toBe(true);
    expect(askable("x".repeat(MAX_QUESTION))).toBe(true);
    expect(askable("x".repeat(MAX_QUESTION + 1))).toBe(false);
  });
});

describe("SUGGESTIONS", () => {
  it("are all askable", () => {
    for (const s of SUGGESTIONS) expect(askable(s)).toBe(true);
  });
});

describe("describeAssistantError", () => {
  const api = (status: number, retry: number | null = null) =>
    new ApiError(status, "code", "backend text", retry);

  it("says what happened in plain words", () => {
    expect(describeAssistantError(new NetworkError(new Error("x")))).toContain("offline");
    expect(describeAssistantError(api(503))).toContain("isn’t available");
    expect(describeAssistantError(api(429, 600))).toContain("in about 10 minutes");
    expect(describeAssistantError(api(429))).toContain("a little later");
    expect(describeAssistantError(api(422))).toContain("couldn’t read that");
  });

  it("never shows the raw backend message", () => {
    expect(describeAssistantError(api(500))).not.toContain("backend text");
    expect(describeAssistantError(new Error("boom"))).not.toContain("boom");
  });
});
