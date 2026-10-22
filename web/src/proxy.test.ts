import { NextRequest } from "next/server";
import { describe, expect, it } from "vitest";

import { proxy } from "./proxy";

const visit = (path: string, cookie?: string) =>
  proxy(new NextRequest(`http://web.test${path}`, cookie ? { headers: { cookie } } : undefined));

describe("request proxy", () => {
  it("serves the landing page to a signed-out visitor", () => {
    const res = visit("/");
    expect(res.headers.get("location")).toBeNull();
    expect(res.headers.get("x-middleware-next")).toBe("1");
  });

  it("sends a signed-in visitor at the landing page to their portal", () => {
    const res = visit("/", "ibh_s=1");
    expect(res.status).toBe(307);
    expect(res.headers.get("location")).toBe("http://web.test/home");
  });

  it("still sends a signed-out visitor at a portal page to sign-in", () => {
    expect(visit("/projects").headers.get("location")).toBe("http://web.test/sign-in?next=%2Fprojects");
  });
});
