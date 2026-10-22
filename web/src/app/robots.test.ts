import { afterEach, describe, expect, it } from "vitest";

import robots from "./robots";
import sitemap from "./sitemap";

afterEach(() => {
  delete process.env.IBH_ENVIRONMENT;
  delete process.env.IBH_SITE_URL;
});

describe("robots and sitemap", () => {
  it("keeps every crawler out outside production", () => {
    process.env.IBH_ENVIRONMENT = "staging";
    process.env.IBH_SITE_URL = "https://staging.example.test";
    expect(robots().rules).toEqual({ userAgent: "*", disallow: "/" });
    expect(sitemap()).toEqual([]);
  });

  it("lets production index the public pages only", () => {
    process.env.IBH_ENVIRONMENT = "production";
    process.env.IBH_SITE_URL = "https://example.test";
    const r = robots();
    expect(r.sitemap).toBe("https://example.test/sitemap.xml");
    expect(JSON.stringify(r.rules)).toContain("/ops");
    expect(sitemap().map((e) => e.url)).toContain("https://example.test/trust");
    expect(sitemap()[0]?.url).toBe("https://example.test");
  });
});
