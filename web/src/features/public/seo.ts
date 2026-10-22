// The public pages a crawler may index (robots.ts, sitemap.ts; e2e/public.spec.ts visits each one).
export const PUBLIC_PATHS = [
  "/",
  "/how-it-works",
  "/pricing",
  "/contractors",
  "/supervisors",
  "/trust",
  "/contact",
  "/privacy",
  "/terms",
];

/** The site's own address without a trailing slash (IBH_SITE_URL), or null when unset. */
export function siteUrl(): string | null {
  const url = process.env.IBH_SITE_URL?.trim();
  return url ? url.replace(/\/+$/, "") : null;
}
