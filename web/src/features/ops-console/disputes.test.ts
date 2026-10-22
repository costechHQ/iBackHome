import { describe, expect, it } from "vitest";

import { ApiError } from "@/common/api/errors";

import { proposalNote, queueChip, resolveConflict, stageFor, timeline } from "./disputes";

const me = "ops-1";
const other = "ops-2";

describe("two-approver resolution", () => {
  it("knows who acts next", () => {
    expect(stageFor({ proposed_by: null }, me)).toBe("needs_proposal");
    expect(stageFor({ proposed_by: me, proposed_outcome: "release" }, me)).toBe("awaiting_other");
    expect(stageFor({ proposed_by: other, proposed_outcome: "release" }, me)).toBe("needs_second");
  });

  it("shows the designed queue chip", () => {
    expect(queueChip({ proposed_by: other })).toEqual({ label: "Waiting for 2nd approver", tone: "warn" });
    expect(queueChip({ proposed_by: null }).tone).toBe("neutral");
  });

  it("treats the backend's 409s as designed states", () => {
    expect(resolveConflict(new ApiError(409, "second_approval_required", "x"))?.title).toBe(
      "You proposed this resolution",
    );
    expect(resolveConflict(new ApiError(409, "resolution_mismatch", "x"))?.title).toBe(
      "That isn't the proposed outcome",
    );
    expect(resolveConflict(new ApiError(409, "dispute_not_open", "x"))?.title).toMatch(/already resolved/);
    expect(resolveConflict(new ApiError(500, "server_error", "x"))).toBeNull();
  });
});

describe("dispute timeline from the audit log", () => {
  const entries = [
    {
      id: "4",
      action: "dispute.resolution_proposed",
      actor_id: me,
      after: { proposed_outcome: "release", resolution_notes: "Wall is fine" },
      at: "2026-10-22T10:00:00Z",
    },
    {
      id: "1",
      action: "milestone.claimed",
      actor_id: "c",
      before: { status: "funded" },
      after: { status: "claimed" },
      at: "2026-10-20T09:00:00Z",
    },
    {
      id: "2",
      action: "milestone.verified",
      actor_id: "s",
      before: { status: "claimed" },
      after: { status: "verified" },
      at: "2026-10-21T09:00:00Z",
    },
    {
      id: "3",
      action: "dispute.opened",
      actor_id: "cl",
      after: { reason: "Cracks in the slab" },
      at: "2026-10-21T12:00:00Z",
    },
    {
      id: "5",
      action: "milestone.funded",
      actor_id: "s",
      before: { status: "claimed" },
      after: { status: "funded" },
      at: "2026-10-19T09:00:00Z",
    },
    { id: "6", action: "evidence.accepted", actor_id: "s", at: "2026-10-21T08:00:00Z" },
  ];

  it("orders the steps, quotes reasons and notes, and marks the viewer's own", () => {
    const items = timeline(entries, "Roofing", me);
    expect(items.map((i) => i.text)).toEqual([
      "The supervisor sent Roofing back",
      "The contractor claimed Roofing",
      "The supervisor verified Roofing",
      "The client raised the dispute",
      "Proposed: release",
    ]);
    expect(items[3]?.quote).toBe("Cracks in the slab");
    expect(items[4]).toMatchObject({ quote: "Wall is fine", byViewer: true });
  });

  it("reads the first approver's note", () => {
    expect(proposalNote(entries)).toBe("Wall is fine");
    expect(proposalNote([])).toBeNull();
  });
});
