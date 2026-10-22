import type { MetadataRoute } from "next";

import { PUBLIC_PATHS, siteUrl } from "@/features/public/seo";

// The public pages, in production only and once IBH_SITE_URL says where the site lives.
export const dynamic = "force-dynamic";

export default function sitemap(): MetadataRoute.Sitemap {
  const base = siteUrl();
  if (process.env.IBH_ENVIRONMENT !== "production" || !base) return [];
  return PUBLIC_PATHS.map((p) => ({ url: `${base}${p === "/" ? "" : p}` }));
}
