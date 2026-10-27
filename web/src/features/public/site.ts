// Everything on the public site that only the company can supply (WEB-PUBLIC-001 to 009). Each value starts
// empty (null); a section that needs an empty value isn't shown, so no "[PLACEHOLDER]" from the designs is
// ever published (e2e/public.spec.ts checks). Fill these in when the product owner has them: no other code
// changes. Prices are text as they should read, e.g. "£45".

export type SiteContent = {
  company: {
    /** Registered company name, e.g. "iBackHome Ltd". */
    registeredName: string | null;
    /** CAC registration number (RC). */
    rcNumber: string | null;
    /** The office address as it should read, e.g. "12 Example Road, Ikeja, Lagos State". */
    officeAddress: string | null;
  };
  contact: {
    email: string | null;
    /** International format, e.g. "+234 800 000 0000". */
    whatsapp: string | null;
    /** e.g. "one working day". */
    responseTime: string | null;
    /** e.g. "Monday to Friday, 9:00 to 17:00". */
    openingHours: string | null;
  };
  trust: {
    escrowPartner: string | null;
    regulator: string | null;
    licenceNumber: string | null;
    dpoName: string | null;
    dpoEmail: string | null;
    trustEmail: string | null;
    /** Where data is hosted and how long it is kept, in a sentence. */
    hostingAndRetention: string | null;
  };
  pricing: {
    /** Monthly supervision per project in each currency. */
    supervisionGbp: string | null;
    supervisionUsd: string | null;
    supervisionEur: string | null;
    /** The funding fee as a percentage, e.g. "2.5%". */
    fundingFee: string | null;
    escrowPartnerFee: string | null;
    materialsCharge: string | null;
    billing: string | null;
    cancellation: string | null;
  };
  contractors: { payout: string | null; fee: string | null };
  supervisors: { ratePerVisit: string | null; vettingTime: string | null; payment: string | null };
};

export const SITE: SiteContent = {
  company: { registeredName: null, rcNumber: null, officeAddress: null },
  contact: {
    email: "hello@ibackhome.com",
    whatsapp: "+234 803 836 2327",
    responseTime: null,
    openingHours: null,
  },
  trust: {
    escrowPartner: null,
    regulator: null,
    licenceNumber: null,
    dpoName: null,
    dpoEmail: null,
    trustEmail: null,
    hostingAndRetention: null,
  },
  pricing: {
    supervisionGbp: null,
    supervisionUsd: null,
    supervisionEur: null,
    fundingFee: null,
    escrowPartnerFee: null,
    materialsCharge: null,
    billing: null,
    cancellation: null,
  },
  contractors: { payout: null, fee: null },
  supervisors: { ratePerVisit: null, vettingTime: null, payment: null },
};

/** "© 2026 iBackHome · Company · RC 123" with only the parts that are known. */
export function copyrightLine(content: SiteContent = SITE, year = new Date().getFullYear()): string {
  const { registeredName, rcNumber } = content.company;
  return [`© ${year} iBackHome`, registeredName, rcNumber ? `RC ${rcNumber}` : null]
    .filter(Boolean)
    .join(" · ");
}

/** True once every value is known (the pricing page then shows prices instead of "being finalised"). */
export function hasPrices(content: SiteContent = SITE): boolean {
  const p = content.pricing;
  return Boolean(p.supervisionGbp && p.fundingFee);
}
