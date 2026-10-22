import { describe, expect, it } from "vitest";

import { contactChannels, whatsappLink } from "./contact";
import { siteUrl } from "./seo";
import { copyrightLine, hasPrices, SITE, type SiteContent } from "./site";

const filled = (patch: (c: SiteContent) => void): SiteContent => {
  const c = structuredClone(SITE);
  patch(c);
  return c;
};

describe("site content", () => {
  it("ships with every company value empty, so no design placeholder can be published", () => {
    const values = Object.values(SITE).flatMap((group) => Object.values(group));
    expect(values.every((v) => v === null)).toBe(true);
  });

  it("builds the copyright line from the parts that are known", () => {
    expect(copyrightLine(SITE, 2026)).toBe("© 2026 iBackHome");
    const known = filled((c) => {
      c.company.registeredName = "Example Ltd";
      c.company.rcNumber = "123";
    });
    expect(copyrightLine(known, 2026)).toBe("© 2026 iBackHome · Example Ltd · RC 123");
  });

  it("shows prices only once the supervision fee and the funding fee are both set", () => {
    expect(hasPrices(SITE)).toBe(false);
    expect(hasPrices(filled((c) => (c.pricing.supervisionGbp = "£1")))).toBe(false);
    const both = filled((c) => {
      c.pricing.supervisionGbp = "£1";
      c.pricing.fundingFee = "1%";
    });
    expect(hasPrices(both)).toBe(true);
  });
});

describe("contact channels", () => {
  it("lists none until they're set, then only the ones that are", () => {
    expect(contactChannels(SITE)).toEqual([]);
    const some = filled((c) => {
      c.contact.whatsapp = "+234 800 000 0000";
      c.contact.openingHours = "Monday to Friday, 9:00 to 17:00";
    });
    expect(contactChannels(some).map((c) => c.label)).toEqual(["WhatsApp", "Hours"]);
  });

  it("links WhatsApp with the digits only", () => {
    expect(whatsappLink("+234 (800) 000-0000")).toBe("https://wa.me/2348000000000");
  });
});

describe("site address", () => {
  it("drops trailing slashes and treats blank as unset", () => {
    process.env.IBH_SITE_URL = "https://example.test//";
    expect(siteUrl()).toBe("https://example.test");
    process.env.IBH_SITE_URL = "  ";
    expect(siteUrl()).toBeNull();
    delete process.env.IBH_SITE_URL;
  });
});
