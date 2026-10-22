import { describe, expect, it } from "vitest";

import { disputeAction, milestoneActions, type ProjectContext, type Viewer } from "./actions";

const project: ProjectContext = {
  status: "active",
  client_id: "client-1",
  contractor_id: "contractor-1",
  supervisor_id: "supervisor-1",
};
const client: Viewer = { id: "client-1", role: "client" };
const contractor: Viewer = { id: "contractor-1", role: "contractor" };
const supervisor: Viewer = { id: "supervisor-1", role: "supervisor" };
const ops: Viewer = { id: "ops-1", role: "ops" };
const otherOps: Viewer = { id: "ops-2", role: "ops" };

const actions = (status: string, viewer: Viewer, p: ProjectContext = project, online = true) => [
  ...milestoneActions({ status }, p, viewer, { online }),
];

describe("milestone actions (state-to-ui.md)", () => {
  it("lets only the client approve, and only a verified milestone", () => {
    expect(actions("verified", client)).toEqual(["approve", "raise_dispute"]);
    for (const status of ["pending", "funded", "claimed", "approved", "disputed", "released"]) {
      expect(actions(status, client), status).not.toContain("approve");
    }
    for (const viewer of [contractor, supervisor, ops]) {
      expect(actions("verified", viewer)).not.toContain("approve");
    }
  });

  it("gives the client nothing to do while the supervisor checks a claim", () => {
    expect(actions("claimed", client)).toEqual([]);
  });

  it("lets the contractor claim a funded milestone of an active project", () => {
    expect(actions("funded", contractor)).toEqual(["claim", "request_materials"]);
    expect(actions("funded", contractor, { ...project, status: "paused" })).toEqual([]);
  });

  it("lets only the assigned supervisor verify or send back", () => {
    expect(actions("claimed", supervisor)).toEqual(["verify", "send_back"]);
    expect(actions("claimed", { id: "supervisor-2", role: "supervisor" })).toEqual([]);
  });

  it("gives nobody an action on an approved milestone (escrow is releasing)", () => {
    for (const viewer of [client, contractor, supervisor, ops])
      expect(actions("approved", viewer)).toEqual([]);
  });

  it("lets the parties only view a dispute; ops act through disputeAction", () => {
    expect(actions("disputed", client)).toEqual(["view_dispute"]);
    expect(actions("disputed", contractor)).toEqual(["view_dispute"]);
    expect(actions("disputed", ops)).toEqual([]);
  });

  it("gives other people's projects no actions", () => {
    expect(actions("verified", { id: "client-2", role: "client" })).toEqual([]);
    expect(actions("funded", { id: "contractor-2", role: "contractor" })).toEqual([]);
  });

  it("pauses approvals on a paused project and every write offline", () => {
    expect(actions("verified", client, { ...project, status: "paused" })).toEqual([]);
    expect(actions("verified", client, project, false)).toEqual([]);
    expect(actions("released", client, project, false)).toEqual(["view_receipt"]);
  });

  it("keeps a completed project read-only", () => {
    expect(actions("verified", client, { ...project, status: "completed" })).toEqual([]);
    expect(actions("released", client, { ...project, status: "completed" })).toEqual(["view_receipt"]);
  });
});

describe("dispute resolution (two different ops users, either outcome)", () => {
  const open = { status: "open", proposed_outcome: null, proposed_by: null };
  const proposed = { status: "open", proposed_outcome: "rework", proposed_by: "ops-1" };

  it("lets the first ops user propose", () => {
    expect(disputeAction(open, ops)).toEqual({ kind: "propose" });
  });

  it("never lets the proposer confirm their own proposal", () => {
    expect(disputeAction(proposed, ops)).toEqual({ kind: "waiting_for_second_approver" });
  });

  it("lets a second ops user confirm the same outcome, rework included", () => {
    expect(disputeAction(proposed, otherOps)).toEqual({ kind: "confirm", outcome: "rework" });
  });

  it("gives clients and contractors no resolution action", () => {
    expect(disputeAction(open, client)).toBeNull();
    expect(disputeAction(proposed, contractor)).toBeNull();
  });

  it("does nothing on a resolved dispute or offline", () => {
    expect(disputeAction({ ...proposed, status: "resolved_reject" }, otherOps)).toBeNull();
    expect(disputeAction(open, ops, { online: false })).toBeNull();
  });
});
