// Navigation for each portal, with the designed labels, order and routes (manifest.json `route`). An item is
// shown only once its screen is built (`ready`), so nobody follows a link to a page that doesn't exist yet.
// Each stage flips the items it builds. The dev gallery can show every item to compare with the designs.

export type NavItem = { label: string; href: string; ready: boolean };

/** Project tabs (ClientTabs), relative to /projects/:id. */
export const CLIENT_PROJECT_TABS = [
  { label: "Overview", path: "", ready: false }, // WEB-CLIENT-009
  { label: "Milestones", path: "/milestones", ready: true }, // WEB-CLIENT-013 (W2)
  { label: "Evidence", path: "/evidence", ready: true }, // WEB-CLIENT-010 (W2)
  { label: "Reports", path: "/reports", ready: false }, // WEB-CLIENT-018
  { label: "Ledger", path: "/ledger", ready: true }, // WEB-CLIENT-017 (W2)
  { label: "Orders", path: "/orders", ready: false }, // WEB-CLIENT-019
  { label: "BoQ", path: "/boq", ready: false }, // WEB-CLIENT-005
  { label: "Site map", path: "/site-map", ready: false }, // WEB-CLIENT-012
] as const;

/** Client mobile bottom nav (ClientNav). Project-scoped items need a current project. */
export const CLIENT_MOBILE_NAV = [
  { label: "Home", path: "/projects", projectScoped: false, ready: true },
  { label: "Milestones", path: "/milestones", projectScoped: true, ready: true },
  { label: "Evidence", path: "/evidence", projectScoped: true, ready: true },
  { label: "Money", path: "/ledger", projectScoped: true, ready: true },
  { label: "Reports", path: "/reports", projectScoped: true, ready: false },
] as const;

/** Contractor top bar (ConTop). */
export const CONTRACTOR_NAV: readonly NavItem[] = [
  { label: "Projects", href: "/c", ready: true }, // WEB-CONTRACTOR-003
  { label: "Orders", href: "/c/orders", ready: false }, // WEB-CONTRACTOR-007
  { label: "Payouts", href: "/c/payouts", ready: false }, // WEB-CONTRACTOR-008
  { label: "Profile", href: "/c/profile", ready: false }, // WEB-CONTRACTOR-009
];

/** Contractor project tabs (ConTop project row), relative to /c/projects/:id. */
export const CONTRACTOR_PROJECT_TABS = [
  { label: "Milestones", path: "/milestones", ready: true }, // WEB-CONTRACTOR-005 (W3)
  { label: "BoQ", path: "/boq", ready: false }, // WEB-CONTRACTOR-004
  { label: "Evidence", path: "/evidence", ready: false },
  { label: "Orders", path: "/orders", ready: false }, // WEB-CONTRACTOR-007
] as const;

export type OpsSection = {
  heading: string | null;
  items: readonly (NavItem & { queue?: "vetting" | "flagged_evidence" | "disputes" })[];
};

/** Ops sidebar. Queue counts come from GET /ops/queue. */
export const OPS_NAV: readonly OpsSection[] = [
  { heading: null, items: [{ label: "Overview", href: "/ops", ready: false }] }, // WEB-OPS-002
  {
    heading: "Queues",
    items: [
      { label: "Vetting", href: "/ops/vetting", ready: false, queue: "vetting" }, // WEB-OPS-003
      { label: "Flagged evidence", href: "/ops/evidence", ready: false, queue: "flagged_evidence" }, // WEB-OPS-005
      { label: "Disputes", href: "/ops/disputes", ready: true, queue: "disputes" }, // WEB-OPS-006 (W3)
    ],
  },
  {
    heading: "Operations",
    items: [
      { label: "Projects", href: "/ops/projects", ready: false }, // WEB-OPS-004
      { label: "Spot checks", href: "/ops/spot-checks", ready: false }, // WEB-OPS-007
      { label: "Suppliers", href: "/ops/suppliers", ready: false }, // WEB-OPS-008
      { label: "Price index", href: "/ops/price-index", ready: false }, // WEB-OPS-009
      { label: "Weekly reports", href: "/ops/reports", ready: false }, // WEB-OPS-010
    ],
  },
  {
    heading: "Records",
    items: [
      { label: "Audit log", href: "/ops/audit", ready: false }, // WEB-OPS-011
      { label: "Agent runs", href: "/ops/agent-runs", ready: false }, // WEB-OPS-011
      { label: "Users", href: "/ops/users", ready: false }, // WEB-OPS-012
    ],
  },
];

/** The gallery shows every item (`all`); the app shows only built ones. */
export function shown<T extends { ready: boolean }>(items: readonly T[], all = false): T[] {
  return items.filter((i) => all || i.ready);
}

export function isActive(pathname: string, href: string, exact = false): boolean {
  if (exact) return pathname === href;
  return pathname === href || pathname.startsWith(`${href}/`);
}

/** A milestone's own pages (detail, approve, dispute, receipt): on phones they bring their own compact header and
 *  action bar, so the portal's top bar, project header and bottom nav step aside (WEB-CLIENT-013/014 mobile). */
export function isMilestonePage(pathname: string): boolean {
  return /^\/projects\/[^/]+\/milestones\/[^/]+/.test(pathname);
}
