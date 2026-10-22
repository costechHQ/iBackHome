import type { MetadataRoute } from "next";

import { PUBLIC_PATHS, siteUrl } from "@/features/public/seo";

// Only production is indexed; staging and local tell every crawler to stay out. Read per request so the
// environment of the running container decides, not the one the image was built in.
export const dynamic = "force-dynamic";

export default function robots(): MetadataRoute.Robots {
  if (process.env.IBH_ENVIRONMENT !== "production") return { rules: { userAgent: "*", disallow: "/" } };
  const base = siteUrl();
  return {
    rules: {
      userAgent: "*",
      allow: PUBLIC_PATHS,
      disallow: ["/api/", "/home", "/welcome", "/projects", "/c", "/ops", "/sign-in"],
    },
    sitemap: base ? `${base}/sitemap.xml` : undefined,
  };
}
