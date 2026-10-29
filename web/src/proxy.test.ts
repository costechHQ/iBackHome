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

describe("redirect host", () => {
  // Docker binds HOSTNAME=0.0.0.0, so Next builds req.url from it; the browser's own host must win.
  const behindDocker = (headers: Record<string, string>) =>
    proxy(new NextRequest("http://0.0.0.0:3000/projects", { headers }));

  it("redirects to the host the browser used, not the bind address", () => {
    const res = behindDocker({ host: "127.0.0.1:3000" });
    expect(res.headers.get("location")).toBe("http://127.0.0.1:3000/sign-in?next=%2Fprojects");
  });

  it("follows the proxy's forwarded host and scheme", () => {
    const res = behindDocker({
      host: "web:3000",
      "x-forwarded-host": "staging.ibackhome.com",
      "x-forwarded-proto": "https",
    });
    expect(res.headers.get("location")).toBe("https://staging.ibackhome.com/sign-in?next=%2Fprojects");
  });
});
