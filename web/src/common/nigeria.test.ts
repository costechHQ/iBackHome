import { describe, expect, it } from "vitest";

import { NIGERIAN_STATES, siteAddress } from "./nigeria";

describe("Nigerian states", () => {
  it("has the 36 states and the FCT, once each", () => {
    expect(NIGERIAN_STATES).toHaveLength(37);
    expect(new Set(NIGERIAN_STATES).size).toBe(37);
  });

  it("writes a site address with the state", () => {
    expect(siteAddress(" 12 Chime Avenue ", "New Haven", "Enugu")).toBe(
      "12 Chime Avenue, New Haven, Enugu State",
    );
    expect(siteAddress("4 Aminu Kano Crescent", "Wuse II", "FCT (Abuja)")).toBe(
      "4 Aminu Kano Crescent, Wuse II, FCT (Abuja)",
    );
  });
});
