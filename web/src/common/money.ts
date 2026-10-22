// Money display. The API sends integer minor units (kobo, pence, cents) plus an ISO 4217 code, and
// fx_rate as a decimal string (NGN per 1 unit of the client currency). Nothing here ever turns money into
// a floating-point number: amounts are split with BigInt and handed to Intl.NumberFormat as decimal strings.

/** Currencies a client can choose; contractors, suppliers and supervisors see NGN only. */
export const CLIENT_CURRENCIES = ["GBP", "USD", "EUR"] as const;
export type ClientCurrency = (typeof CLIENT_CURRENCIES)[number];

// en-GB grouping as on the designs ("£1,600.00", "₦10,530,000"); narrowSymbol gives "$" rather than "US$".
const LOCALE = "en-GB";

export function minorDigits(currency: string): number {
  return (
    new Intl.NumberFormat(LOCALE, { style: "currency", currency }).resolvedOptions().maximumFractionDigits ??
    2
  );
}

function toBigInt(amountMinor: number | bigint): bigint {
  if (typeof amountMinor === "bigint") return amountMinor;
  if (!Number.isSafeInteger(amountMinor)) {
    throw new TypeError(`Money must be an integer number of minor units, got ${amountMinor}`);
  }
  return BigInt(amountMinor);
}

/** "-12.05" style decimal string for an integer number of minor units. */
function decimalString(minor: bigint, digits: number): string {
  const negative = minor < 0n;
  const abs = negative ? -minor : minor;
  const scale = 10n ** BigInt(digits);
  const whole = abs / scale;
  const frac = (abs % scale).toString().padStart(digits, "0");
  return `${negative ? "-" : ""}${whole}${digits > 0 ? `.${frac}` : ""}`;
}

/** Rounds an integer number of minor units to whole major units, half away from zero. */
function roundToWhole(minor: bigint, digits: number): bigint {
  const scale = 10n ** BigInt(digits);
  const half = scale / 2n;
  const abs = minor < 0n ? -minor : minor;
  const whole = (abs + half) / scale;
  return minor < 0n ? -whole : whole;
}

export type MoneyFormat = {
  /** "always": 2 decimals (client currencies by default). "auto": decimals only when non-zero (NGN by default).
   *  "whole": rounded to whole units, for estimates shown as "≈ £3,875". */
  decimals?: "always" | "auto" | "whole";
};

export function formatMoney(
  amountMinor: number | bigint,
  currency: string,
  { decimals }: MoneyFormat = {},
): string {
  const minor = toBigInt(amountMinor);
  const digits = minorDigits(currency);
  const mode = decimals ?? (currency === "NGN" ? "auto" : "always");
  const scale = 10n ** BigInt(digits);

  let value: string;
  let fractionDigits: number;
  if (mode === "whole") {
    value = roundToWhole(minor, digits).toString();
    fractionDigits = 0;
  } else if (mode === "auto" && minor % scale === 0n) {
    value = (minor / scale).toString();
    fractionDigits = 0;
  } else {
    value = decimalString(minor, digits);
    fractionDigits = digits;
  }

  return new Intl.NumberFormat(LOCALE, {
    style: "currency",
    currency,
    currencyDisplay: "narrowSymbol",
    minimumFractionDigits: fractionDigits,
    maximumFractionDigits: fractionDigits,
  }).format(value as Intl.StringNumericLiteral);
}

const DECIMAL = /^-?\d+(\.\d+)?$/;

/** Rounds a decimal string to `places`, half away from zero, without floats. */
export function roundDecimal(value: string, places: number): string {
  if (!DECIMAL.test(value)) throw new TypeError(`Not a decimal string: ${value}`);
  const negative = value.startsWith("-");
  const [whole = "0", frac = ""] = (negative ? value.slice(1) : value).split(".");
  const padded = (frac + "0".repeat(places + 1)).slice(0, places + 1);
  let scaled = BigInt(whole + padded.slice(0, places));
  if (Number(padded[places]) >= 5) scaled += 1n;
  const out = decimalString(scaled, places);
  return negative && scaled !== 0n ? `-${out}` : out;
}

/** "£1 = ₦1,950.00": the rate recorded for a transaction (NGN per 1 unit of `currency`). */
export function formatFxRate(fxRate: string, currency: string): string {
  const one = new Intl.NumberFormat(LOCALE, {
    style: "currency",
    currency,
    currencyDisplay: "narrowSymbol",
    maximumFractionDigits: 0,
  }).format(1);
  const naira = new Intl.NumberFormat(LOCALE, {
    style: "currency",
    currency: "NGN",
    currencyDisplay: "narrowSymbol",
    minimumFractionDigits: 2,
    maximumFractionDigits: 2,
  }).format(roundDecimal(fxRate, 2) as Intl.StringNumericLiteral);
  return `${one} = ${naira}`;
}

/** Adds amounts in one currency; refuses to mix currencies. */
export function sumMinor(
  items: readonly { amount_minor: number; currency: string }[],
  currency: string,
): bigint {
  let total = 0n;
  for (const item of items) {
    if (item.currency !== currency) {
      throw new TypeError(`Cannot add ${item.currency} to ${currency}`);
    }
    total += toBigInt(item.amount_minor);
  }
  return total;
}
