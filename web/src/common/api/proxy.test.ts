import { NextRequest } from "next/server";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";

import { resetRefreshCache } from "../auth/refresh";
import { refreshAndReturn, signOut, verifyOtp } from "../auth/session";
import { proxyToApi } from "./proxy";

const SITE = "http://web.test";
const API = "http://api.test";

const jwt = (exp: number) => `h.${btoa(JSON.stringify({ exp }))}.s`;
const now = () => Math.floor(Date.now() / 1000);
const fresh = jwt(now() + 600);
const expired = jwt(now() - 10);

type Call = { url: string; method: string; headers: Headers; body: string | null };
let calls: Call[];
let backend: (call: Call) => Response;

function json(status: number, body: unknown, headers: Record<string, string> = {}) {
  return new Response(JSON.stringify(body), {
    status,
    headers: { "content-type": "application/json", ...headers },
  });
}

beforeEach(() => {
  process.env.API_INTERNAL_URL = API;
  resetRefreshCache();
  calls = [];
  backend = () => json(200, { ok: true });
  vi.stubGlobal("fetch", async (input: string, init: RequestInit = {}) => {
    const call: Call = {
      url: input,
      method: init.method ?? "GET",
      headers: new Headers(init.headers),
      body:
        init.body instanceof ArrayBuffer
          ? new TextDecoder().decode(init.body)
          : typeof init.body === "string"
            ? init.body
            : null,
    };
    calls.push(call);
    return backend(call);
  });
});
afterEach(() => vi.unstubAllGlobals());

function request(
  path: string,
  {
    method = "GET",
    cookies = {},
    body,
    origin = SITE,
    headers = {},
  }: {
    method?: string;
    cookies?: Record<string, string>;
    body?: unknown;
    origin?: string | null;
    headers?: Record<string, string>;
  } = {},
) {
  const h = new Headers({ host: "web.test", ...headers });
  if (origin) h.set("origin", origin);
  const cookie = Object.entries(cookies)
    .map(([k, v]) => `${k}=${v}`)
    .join("; ");
  if (cookie) h.set("cookie", cookie);
  if (body !== undefined) h.set("content-type", "application/json");
  return new NextRequest(`${SITE}${path}`, {
    method,
    headers: h,
    body: body === undefined ? undefined : JSON.stringify(body),
  });
}

const segments = (path: string) =>
  path
    .replace(/^\/api\/v1\//, "")
    .split("?")[0]!
    .split("/");
const proxy = (path: string, init?: Parameters<typeof request>[1]) =>
  proxyToApi(request(path, init), segments(path));

describe("API proxy", () => {
  it("adds the bearer token from the cookie and never stores the answer", async () => {
    const res = await proxy("/api/v1/me", { cookies: { ibh_at: fresh, ibh_rt: "rt-0" } });
    expect(res.status).toBe(200);
    expect(res.headers.get("cache-control")).toBe("no-store");
    expect(calls).toHaveLength(1);
    expect(calls[0]?.url).toBe(`${API}/api/v1/me`);
    expect(calls[0]?.headers.get("authorization")).toBe(`Bearer ${fresh}`);
  });

  it("never forwards the browser's cookies or its own Authorization header", async () => {
    await proxy("/api/v1/me", { cookies: { ibh_at: fresh }, headers: { authorization: "Bearer forged" } });
    expect(calls[0]?.headers.get("cookie")).toBeNull();
    expect(calls[0]?.headers.get("authorization")).toBe(`Bearer ${fresh}`);
  });

  it("refuses to proxy the routes that answer with tokens", async () => {
    for (const path of ["/api/v1/auth/otp/verify", "/api/v1/auth/refresh"]) {
      const res = await proxy(path, { method: "POST", body: {} });
      expect(res.status, path).toBe(404);
    }
    expect(calls).toHaveLength(0);
  });

  it("refuses writes from another site (CSRF) or without an Origin", async () => {
    const evil = await proxy("/api/v1/milestones/m1/approve", {
      method: "POST",
      cookies: { ibh_at: fresh },
      origin: "https://evil.example",
      body: {},
    });
    const none = await proxy("/api/v1/milestones/m1/approve", {
      method: "POST",
      cookies: { ibh_at: fresh },
      origin: null,
      body: {},
    });
    expect(evil.status).toBe(403);
    expect(none.status).toBe(403);
    expect(calls).toHaveLength(0);
  });

  it("forwards the Idempotency-Key and the body of a write", async () => {
    await proxy("/api/v1/milestones/m1/approve", {
      method: "POST",
      cookies: { ibh_at: fresh },
      headers: { "idempotency-key": "key-1" },
      body: { note: "ok" },
    });
    expect(calls[0]?.method).toBe("POST");
    expect(calls[0]?.headers.get("idempotency-key")).toBe("key-1");
    expect(calls[0]?.body).toBe(JSON.stringify({ note: "ok" }));
  });

  it("passes on only the last X-Forwarded-For hop", async () => {
    await proxy("/api/v1/me", {
      cookies: { ibh_at: fresh },
      headers: { "x-forwarded-for": "6.6.6.6, 203.0.113.9" },
    });
    expect(calls[0]?.headers.get("x-forwarded-for")).toBe("203.0.113.9");
  });

  it("refreshes an expired access token first, then sets the rotated cookies", async () => {
    backend = (call) =>
      call.url.endsWith("/auth/refresh")
        ? json(200, { access_token: fresh, refresh_token: "rt-1", expires_in: 900 })
        : json(200, { ok: true });
    const res = await proxy("/api/v1/me", { cookies: { ibh_at: expired, ibh_rt: "rt-0" } });
    expect(calls.map((c) => c.url)).toEqual([`${API}/api/v1/auth/refresh`, `${API}/api/v1/me`]);
    expect(calls[1]?.headers.get("authorization")).toBe(`Bearer ${fresh}`);
    expect(res.cookies.get("ibh_rt")?.value).toBe("rt-1");
    expect(res.cookies.get("ibh_at")?.httpOnly).toBe(true);
    expect(await res.text()).not.toContain("rt-1");
  });

  it("on a 401 refreshes once and replays the same write with the same key", async () => {
    let first = true;
    backend = (call) => {
      if (call.url.endsWith("/auth/refresh"))
        return json(200, { access_token: fresh, refresh_token: "rt-1", expires_in: 900 });
      if (first) {
        first = false;
        return json(401, { error: { code: "unauthorized", message: "Invalid access token." } });
      }
      return json(200, { ok: true });
    };
    const res = await proxy("/api/v1/milestones/m1/approve", {
      method: "POST",
      cookies: { ibh_at: fresh, ibh_rt: "rt-0" },
      headers: { "idempotency-key": "key-1" },
      body: {},
    });
    expect(res.status).toBe(200);
    const writes = calls.filter((c) => c.url.endsWith("/approve"));
    expect(writes).toHaveLength(2);
    expect(writes.map((c) => c.headers.get("idempotency-key"))).toEqual(["key-1", "key-1"]);
    expect(calls.filter((c) => c.url.endsWith("/auth/refresh"))).toHaveLength(1);
  });

  it("ends the session when the refresh is refused, without retrying it", async () => {
    backend = () => json(401, { error: { code: "refresh_token_reused", message: "..." } });
    const res = await proxy("/api/v1/me", { cookies: { ibh_at: expired, ibh_rt: "rt-0" } });
    expect(res.status).toBe(401);
    expect(((await res.json()) as { error: { code: string } }).error.code).toBe("session_expired");
    expect(res.cookies.get("ibh_rt")?.value).toBe("");
    expect(calls).toHaveLength(1);
  });

  it("lets a stale session still request a login code", async () => {
    backend = () => json(202, { status: "sent", expires_in: 300 });
    const res = await proxy("/api/v1/auth/otp/request", {
      method: "POST",
      cookies: { ibh_at: expired, ibh_rt: "rt-dead" },
      body: { identifier: "+2348030000000" },
    });
    expect(res.status).toBe(202);
    expect(calls.map((c) => c.url)).toEqual([`${API}/api/v1/auth/otp/request`]);
    expect(calls[0]?.headers.get("authorization")).toBeNull();
  });

  it("answers 502 with our error shape when the backend is down", async () => {
    backend = () => {
      throw new TypeError("fetch failed");
    };
    const res = await proxy("/api/v1/me", { cookies: { ibh_at: fresh } });
    expect(res.status).toBe(502);
    expect(((await res.json()) as { error: { code: string } }).error.code).toBe("upstream_unreachable");
  });
});

describe("session routes", () => {
  it("verify keeps the tokens in httpOnly cookies and returns only the role and home", async () => {
    backend = (call) =>
      call.url.endsWith("/auth/otp/verify")
        ? json(200, { access_token: fresh, refresh_token: "rt-1", token_type: "bearer", expires_in: 900 })
        : json(200, { role: "client" });
    const res = await verifyOtp(
      request("/api/session/verify", { method: "POST", body: { identifier: "a@b.c", code: "123456" } }),
    );
    const body = await res.text();
    expect(JSON.parse(body)).toEqual({ role: "client", home: "/projects" });
    expect(body).not.toContain("rt-1");
    expect(res.cookies.get("ibh_at")).toMatchObject({
      httpOnly: true,
      secure: true,
      sameSite: "lax",
      path: "/",
    });
    expect(res.cookies.get("ibh_rt")).toMatchObject({ httpOnly: true, path: "/api" });
  });

  it("verify passes the backend's login-code error through", async () => {
    backend = () => json(400, { error: { code: "invalid_code", message: "This code is not valid." } });
    const res = await verifyOtp(
      request("/api/session/verify", { method: "POST", body: { identifier: "a@b.c", code: "000000" } }),
    );
    expect(res.status).toBe(400);
    expect(((await res.json()) as { error: { code: string } }).error.code).toBe("invalid_code");
    expect(res.cookies.get("ibh_at")).toBeUndefined();
  });

  it("refresh-and-return goes back to a local path only", async () => {
    backend = () => json(200, { access_token: fresh, refresh_token: "rt-1", expires_in: 900 });
    const ok = await refreshAndReturn(
      request("/api/session/refresh?next=/projects/p1", { cookies: { ibh_rt: "rt-0" } }),
    );
    expect(ok.status).toBe(303);
    expect(ok.headers.get("location")).toBe(`${SITE}/projects/p1`);
    resetRefreshCache();
    const evil = await refreshAndReturn(
      request("/api/session/refresh?next=//evil.example", { cookies: { ibh_rt: "rt-0" } }),
    );
    expect(evil.headers.get("location")).toBe(`${SITE}/`);
  });

  it("refresh-and-return sends an ended session to sign-in and clears the cookies", async () => {
    backend = () => json(401, { error: { code: "invalid_refresh_token", message: "..." } });
    const res = await refreshAndReturn(
      request("/api/session/refresh?next=/ops", { cookies: { ibh_rt: "rt-0" } }),
    );
    expect(res.headers.get("location")).toBe(`${SITE}/sign-in?next=%2Fops&expired=1`);
    expect(res.cookies.get("ibh_s")?.value).toBe("");
  });

  it("sign-out clears the cookies and refuses other sites", async () => {
    const res = signOut(request("/api/session/sign-out", { method: "POST" }));
    expect(res.status).toBe(204);
    expect(res.cookies.get("ibh_at")?.value).toBe("");
    expect(
      signOut(request("/api/session/sign-out", { method: "POST", origin: "https://evil.example" })).status,
    ).toBe(403);
  });
});
