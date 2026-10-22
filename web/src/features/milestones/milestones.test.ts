import { describe, expect, it } from "vitest";

import { checkResults } from "@/common/ui/evidence";

import { activityFor } from "./activity";
import { milestoneNeedingAttention } from "./attention";
import { conflictCopy } from "./conflict";

const ms = (status: string, sequence: number) => ({ id: `m${sequence}`, status, sequence });

describe("milestoneNeedingAttention", () => {
  it("opens the milestone waiting for the client first", () => {
    expect(milestoneNeedingAttention([ms("released", 1), ms("claimed", 2), ms("verified", 3)])?.id).toBe(
      "m3",
    );
  });

  it("then a dispute or a release in progress, then work in progress", () => {
    expect(milestoneNeedingAttention([ms("released", 1), ms("disputed", 2), ms("claimed", 3)])?.id).toBe(
      "m2",
    );
    expect(milestoneNeedingAttention([ms("released", 1), ms("funded", 2), ms("claimed", 3)])?.id).toBe("m3");
    expect(milestoneNeedingAttention([ms("released", 1), ms("pending", 2)])?.id).toBe("m2");
  });

  it("falls back to the last milestone when everything is released", () => {
    expect(milestoneNeedingAttention([ms("released", 2), ms("released", 1)])?.id).toBe("m2");
    expect(milestoneNeedingAttention([])).toBeUndefined();
  });
});

describe("activityFor", () => {
  it("lists what happened, newest first, naming people by role", () => {
    const events = activityFor({
      milestone: {
        name: "Roofing",
        funded_at: "2026-10-22T05:00:00Z",
        claimed_at: "2026-10-23T05:00:00Z",
        verified_at: "2026-10-24T05:00:00Z",
        approved_at: null,
        released_at: null,
      } as never,
      money: { payment: { at: "2026-10-22T04:59:59Z" } as never },
    });
    expect(events.map((e) => e.text)).toEqual([
      "Verified by the supervisor",
      "The contractor claimed Roofing is finished",
      "Funded: escrow partner confirmed the hold",
      "You paid by card",
    ]);
  });
});

describe("conflictCopy (409)", () => {
  it("says the approval already happened, nothing sent twice", () => {
    expect(conflictCopy("Roofing", "approved")).toEqual({
      title: "Roofing was already approved",
      body: "You approved it on another device or tab, so nothing was sent twice. The release is in progress.",
    });
  });

  it("says a dispute paused it, and covers anything else", () => {
    expect(conflictCopy("Roofing", "disputed").title).toBe("Roofing is under dispute");
    expect(conflictCopy("Roofing", "funded").title).toBe("Roofing changed while you were deciding");
  });
});

describe("checkResults (the three checks from the evidence state)", () => {
  it("passes all three for accepted evidence", () => {
    expect(checkResults("accepted")).toEqual({ geofence: "pass", signature: "pass", reuse: "pass" });
  });

  it("puts only the reuse check under review for flagged evidence", () => {
    expect(checkResults("flagged")).toEqual({ geofence: "pass", signature: "pass", reuse: "review" });
  });

  it("follows the server's check order: earlier checks passed, later ones never ran", () => {
    // Reasons exactly as backend features/evidence/checks.py writes them.
    expect(checkResults("rejected", "The signature is not valid for this device.")).toEqual({
      geofence: "pending",
      signature: "fail",
      reuse: "pending",
    });
    expect(
      checkResults("rejected", "The capture was uploaded more than 72 hours after it was taken."),
    ).toEqual({ geofence: "pending", signature: "pass", reuse: "pending" });
    expect(checkResults("rejected", "The capture was taken 62 m outside the site.")).toEqual({
      geofence: "fail",
      signature: "pass",
      reuse: "pending",
    });
    expect(checkResults("rejected", "The file does not match the hash the device signed.")).toEqual({
      geofence: "pending",
      signature: "pending",
      reuse: "fail",
    });
    expect(checkResults("rejected", "Reviewed by ops: a copy of an earlier photo.")).toEqual({
      geofence: "pending",
      signature: "pending",
      reuse: "pending",
    });
  });

  it("shows nothing checked yet while checks run", () => {
    expect(checkResults("pending_checks")).toEqual({
      geofence: "pending",
      signature: "pending",
      reuse: "pending",
    });
  });
});
