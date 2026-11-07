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
  it("ships with every company value empty except the published WhatsApp number and email", () => {
    const { email, whatsapp, ...contact } = SITE.contact;
    const { fundingFee, ...pricing } = SITE.pricing;
    expect(fundingFee).toBe("2.5%"); // the backend's FUNDING_FEE_BPS=250
    expect(email).toBe("hello@ibackhome.com");
    expect(whatsapp).toBe("+234 803 836 2327");
    const values = Object.values({ ...SITE, contact, pricing }).flatMap((group) => Object.values(group));
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

  it("treats the funding fee as unpriced only while it is empty", () => {
    expect(hasPrices(SITE)).toBe(true);
    expect(hasPrices(filled((c) => (c.pricing.fundingFee = null)))).toBe(false);
  });
});

describe("contact channels", () => {
  it("lists only the channels that are set", () => {
    expect(contactChannels(SITE).map((c) => c.label)).toEqual(["Call / WhatsApp", "Email"]);
    const some = filled((c) => {
      c.contact.email = null;
      c.contact.whatsapp = "+234 800 000 0000";
      c.contact.openingHours = "Monday to Friday, 9:00 to 17:00";
    });
    expect(contactChannels(some).map((c) => c.label)).toEqual(["Call / WhatsApp", "Hours"]);
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
