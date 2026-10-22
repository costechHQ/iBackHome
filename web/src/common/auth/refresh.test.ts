import { beforeEach, describe, expect, it, vi } from "vitest";

import { tokenExpiry, needsRefresh } from "./jwt";
import { RefreshFailed, refreshSession, resetRefreshCache, REUSE_WINDOW_MS } from "./refresh";

const pair = (n: number) => ({ access_token: `at-${n}`, refresh_token: `rt-${n}`, expires_in: 900 });

describe("single-flight refresh", () => {
  beforeEach(resetRefreshCache);

  it("calls the backend once for many concurrent requests with the same refresh token", async () => {
    let resolve!: (v: ReturnType<typeof pair>) => void;
    const refresh = vi.fn(() => new Promise<ReturnType<typeof pair>>((r) => (resolve = r)));
    const calls = Array.from({ length: 10 }, () => refreshSession("rt-0", { refresh }));
    resolve(pair(1));
    const results = await Promise.all(calls);
    expect(refresh).toHaveBeenCalledTimes(1);
    expect(new Set(results.map((r) => r.refresh_token))).toEqual(new Set(["rt-1"]));
  });

  it("gives a late request that still carries the old token the same new pair, without reusing the old token", async () => {
    let t = 0;
    const refresh = vi.fn(async () => pair(1));
    await refreshSession("rt-0", { refresh, now: () => t });
    t = REUSE_WINDOW_MS - 1;
    await expect(refreshSession("rt-0", { refresh, now: () => t })).resolves.toEqual(pair(1));
    expect(refresh).toHaveBeenCalledTimes(1);
  });

  it("never retries a failed refresh: later callers get the same failure", async () => {
    const refresh = vi.fn(async () => {
      throw new RefreshFailed("refresh_token_reused");
    });
    await expect(refreshSession("rt-0", { refresh })).rejects.toThrow(RefreshFailed);
    await expect(refreshSession("rt-0", { refresh })).rejects.toThrow(RefreshFailed);
    expect(refresh).toHaveBeenCalledTimes(1);
  });

  it("forgets old entries after the reuse window", async () => {
    let t = 0;
    const refresh = vi.fn(async () => pair(1));
    await refreshSession("rt-0", { refresh, now: () => t });
    t = REUSE_WINDOW_MS + 1;
    await refreshSession("rt-other", { refresh, now: () => t });
    await refreshSession("rt-0", { refresh, now: () => t });
    expect(refresh).toHaveBeenCalledTimes(3);
  });

  it("keeps different sessions apart", async () => {
    const refresh = vi.fn(async (token: string) => ({ ...pair(9), refresh_token: `${token}-next` }));
    const [a, b] = await Promise.all([
      refreshSession("rt-a", { refresh }),
      refreshSession("rt-b", { refresh }),
    ]);
    expect(a.refresh_token).toBe("rt-a-next");
    expect(b.refresh_token).toBe("rt-b-next");
  });
});

describe("token expiry", () => {
  const jwt = (payload: object) =>
    `x.${btoa(JSON.stringify(payload)).replace(/\+/g, "-").replace(/\//g, "_").replace(/=+$/, "")}.y`;

  it("reads exp without verifying", () => {
    expect(tokenExpiry(jwt({ exp: 1_000 }))).toBe(1_000);
    expect(tokenExpiry("not-a-jwt")).toBeNull();
    expect(tokenExpiry(undefined)).toBeNull();
  });

  it("refreshes a little before expiry", () => {
    expect(needsRefresh(jwt({ exp: 1_000 }), 900)).toBe(false);
    expect(needsRefresh(jwt({ exp: 1_000 }), 975)).toBe(true);
    expect(needsRefresh(undefined, 0)).toBe(true);
  });
});
