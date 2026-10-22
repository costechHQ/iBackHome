// Country and time zone choices for the client's location step: every IANA zone the browser knows, labelled
// like the design ("London (BST, UTC+1)"), and a first guess at the country from the phone number or the
// browser. The backend checks both.

import { COMMON_ISO, COUNTRIES } from "@/common/countries";
import { dialOf } from "@/features/auth/otp";

export type ZoneOption = { value: string; label: string };

function city(zone: string): string {
  return (zone.split("/").pop() ?? zone).replace(/_/g, " ");
}

function part(zone: string, now: Date, style: "short" | "shortOffset"): string {
  try {
    const parts = new Intl.DateTimeFormat("en-GB", { timeZone: zone, timeZoneName: style }).formatToParts(
      now,
    );
    return parts.find((p) => p.type === "timeZoneName")?.value ?? "";
  } catch {
    return "";
  }
}

/** "London (BST, UTC+1)"; "UTC" stays "UTC". */
export function zoneLabel(zone: string, now: Date = new Date()): string {
  if (zone === "UTC") return "UTC";
  const offset = part(zone, now, "shortOffset").replace("GMT", "UTC").replace(/^UTC$/, "UTC+0");
  const short = part(zone, now, "short");
  const name = short && !short.startsWith("GMT") ? `${short}, ${offset}` : offset;
  return `${city(zone)} (${name})`;
}

export function zoneOptions(now: Date = new Date()): ZoneOption[] {
  const zones =
    typeof Intl.supportedValuesOf === "function"
      ? Intl.supportedValuesOf("timeZone")
      : ["Africa/Lagos", "Europe/London"];
  return [...new Set([...zones, "UTC"])]
    .map((value) => ({ value, label: zoneLabel(value, now) }))
    .sort((a, b) => a.label.localeCompare(b.label));
}

export function browserZone(): string | null {
  try {
    return Intl.DateTimeFormat().resolvedOptions().timeZone || null;
  } catch {
    return null;
  }
}

/** A first guess at where someone lives: their phone's country code, else the browser's region. */
export function guessCountry(phone: string | null | undefined, locale?: string): string | null {
  const dial = phone ? dialOf(phone) : null;
  if (dial) {
    // In the common countries' order, so +1 is the United States before Canada.
    const common = COMMON_ISO.find((iso) => COUNTRIES.some((c) => c.iso === iso && c.dial === dial));
    const any = COUNTRIES.find((c) => c.dial === dial);
    if (common ?? any) return common ?? any!.iso;
  }
  const region = (locale ?? "").split("-")[1]?.toUpperCase();
  return region && COUNTRIES.some((c) => c.iso === region) ? region : null;
}
