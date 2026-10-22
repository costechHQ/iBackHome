// Times arrive from the API as UTC ISO 8601 strings. Clients see their own time zone (GET /me timezone);
// contractors, supervisors, suppliers and ops see WAT. The UTC time is offered on hover where designed.

export const WAT = "Africa/Lagos";
const LOCALE = "en-GB";

export function viewerTimeZone(me: { role: string; timezone?: string | null }): string {
  if (me.role === "client" && me.timezone && isValidTimeZone(me.timezone)) return me.timezone;
  return WAT;
}

export function isValidTimeZone(tz: string): boolean {
  try {
    new Intl.DateTimeFormat(LOCALE, { timeZone: tz });
    return true;
  } catch {
    return false;
  }
}

function toDate(iso: string): Date {
  const d = new Date(iso);
  if (Number.isNaN(d.getTime())) throw new TypeError(`Not a date: ${iso}`);
  return d;
}

function part(parts: Intl.DateTimeFormatPart[], type: Intl.DateTimeFormatPartTypes): string {
  return parts.find((p) => p.type === type)?.value ?? "";
}

/** Short zone label: "WAT" for Lagos (Intl says "GMT+1"), otherwise the locale's short name ("GMT", "BST"). */
export function zoneLabel(iso: string, tz: string): string {
  if (tz === WAT) return "WAT";
  const parts = new Intl.DateTimeFormat(LOCALE, { timeZone: tz, timeZoneName: "short" }).formatToParts(
    toDate(iso),
  );
  return part(parts, "timeZoneName");
}

/** "Mon 30 Nov", with the year added when it isn't the current year in that zone. */
export function formatDate(iso: string, tz: string, now: Date = new Date()): string {
  const d = toDate(iso);
  const year = (x: Date) => new Intl.DateTimeFormat(LOCALE, { timeZone: tz, year: "numeric" }).format(x);
  const parts = new Intl.DateTimeFormat(LOCALE, {
    timeZone: tz,
    weekday: "short",
    day: "numeric",
    month: "short",
    year: "numeric",
  }).formatToParts(d);
  const base = `${part(parts, "weekday")} ${part(parts, "day")} ${part(parts, "month")}`;
  return year(d) === year(now) ? base : `${base} ${part(parts, "year")}`;
}

/** "09:12 GMT" (24-hour, with the zone). */
export function formatTime(iso: string, tz: string): string {
  const time = new Intl.DateTimeFormat(LOCALE, {
    timeZone: tz,
    hour: "2-digit",
    minute: "2-digit",
    hourCycle: "h23",
  }).format(toDate(iso));
  return `${time} ${zoneLabel(iso, tz)}`;
}

/** "Fri 8 Jan, 08:10 WAT". */
export function formatDateTime(iso: string, tz: string, now: Date = new Date()): string {
  return `${formatDate(iso, tz, now)}, ${formatTime(iso, tz)}`;
}

/** For hover text: "2026-12-14 09:12 UTC". */
export function formatUtc(iso: string): string {
  const d = toDate(iso);
  return `${d.toISOString().slice(0, 16).replace("T", " ")} UTC`;
}
