import { describe, expect, it } from "vitest";

import { nowText, oldest, projectFlags, waited } from "./ops";

const NOW = new Date("2026-10-22T12:00:00Z");

describe("queue ages", () => {
  it("says minutes, hours, then days", () => {
    expect(waited("2026-10-22T11:48:00Z", NOW)).toBe("12 min");
    expect(waited("2026-10-22T07:00:00Z", NOW)).toBe("5 h");
    expect(waited("2026-10-20T11:00:00Z", NOW)).toBe("2 days");
    expect(waited("2026-10-22T12:05:00Z", NOW)).toBe("0 min");
  });

  it("finds the oldest", () => {
    expect(oldest(["2026-10-22T10:00:00Z", "2026-10-21T10:00:00Z"])).toBe("2026-10-21T10:00:00Z");
    expect(oldest([])).toBeNull();
  });
});

describe("what a project needs from ops", () => {
  const m = (sequence: number, status: string, rejected = false) => ({
    name: `M${sequence}`,
    sequence,
    status,
    latest_verification: rejected ? { decision: "rejected" } : null,
  });

  it("flags a BoQ waiting for ops, a live project with no supervisor, disputes and rework", () => {
    expect(projectFlags({ status: "boq_review", supervisor_id: null }, [], true)).toEqual([
      { label: "Needs ops approval", tone: "warn" },
    ]);
    expect(
      projectFlags({ status: "active", supervisor_id: null }, [m(1, "disputed"), m(2, "funded", true)]).map(
        (f) => f.label,
      ),
    ).toEqual(["No supervisor", "Disputed", "Sent back"]);
    expect(projectFlags({ status: "active", supervisor_id: "s" }, [m(1, "released")])).toEqual([]);
    expect(projectFlags({ status: "draft", supervisor_id: null }, [])).toEqual([]);
  });

  it("says what is happening now", () => {
    expect(nowText({ status: "draft" }, [])).toBe("Setup · waiting for the BoQ");
    expect(nowText({ status: "active" }, [m(2, "claimed"), m(1, "released")])).toBe("M2 · claimed");
    expect(nowText({ status: "active" }, [m(1, "funded", true)])).toBe("M1 · rework");
    expect(nowText({ status: "completed" }, [m(1, "released")])).toBe("All milestones released");
  });
});
