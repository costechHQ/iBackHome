// Mock adapters for data the backend doesn't serve yet (Docs/design/04-api-mapping/missing-endpoints.md).
// Each one returns the sample from the screen's fixtures.json `mock_adapters`, and only when its gap is switched
// on by IBH_MOCKS (read on the server, passed down by the portal layout): "all", or a list like "MX-10,MX-03".
// Docker Compose turns them on locally and on staging; production leaves IBH_MOCKS unset, and the element a
// mock would fill is hidden instead. Nothing here is real data: never use it outside this folder's callers.

export type MockGap = "MX-03" | "MX-06" | "MX-10";
export type MockFlags = readonly MockGap[];

const ALL: MockFlags = ["MX-03", "MX-06", "MX-10"];

/** Parses IBH_MOCKS. Unknown ids are ignored. */
export function parseMockFlags(value: string | undefined): MockFlags {
  if (!value) return [];
  if (value.trim() === "all") return ALL;
  const asked = value.split(",").map((s) => s.trim());
  return ALL.filter((gap) => asked.includes(gap));
}

/** MX-03 (payout recipient): who the release pays, with the masked account (WEB-CLIENT-013 fixtures). */
export function mockPayee(): { name: string; bank: string; accountMasked: string } {
  return { name: "Obi Building Works", bank: "First Bank", accountMasked: "******6789" };
}

/** MX-10 (dispute reads): a raised dispute's reason and state, keyed to the real milestone (WEB-CLIENT-015). */
export function mockDispute(milestoneId: string): {
  milestoneId: string;
  reason: string;
  status: "open";
  raisedAt: string;
} {
  return {
    milestoneId,
    reason: "Rear gutter outlet is blocked; please check before release.",
    status: "open",
    raisedAt: "2026-12-12T09:20:00Z",
  };
}

/** MX-06 (payout history): the contractor's payouts and bank account (WEB-CONTRACTOR-003 fixtures). */
export function mockPayouts(): {
  items: { reference: string; amountMinor: number; reason: string; completedAt: string }[];
  bankName: string;
  accountMasked: string;
} {
  return {
    items: [
      {
        reference: "P-0912",
        amountMinor: 1_326_000_000,
        reason: "Roofing release",
        completedAt: "2026-12-12T09:31:00Z",
      },
      {
        reference: "P-0874",
        amountMinor: 507_000_000,
        reason: "Blockwork to Lintel release",
        completedAt: "2026-11-27T09:14:00Z",
      },
    ],
    bankName: "First Bank of Nigeria",
    accountMasked: "******6789",
  };
}
