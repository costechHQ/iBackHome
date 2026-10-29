import { afterEach, describe, expect, it, vi } from "vitest";

import { setSessionCookies } from "./cookies";

const tokens = { access_token: "at", refresh_token: "rt", expires_in: 900 };

function secureFlags(): boolean[] {
  const seen: boolean[] = [];
  setSessionCookies({ set: (_name, _value, options) => void seen.push(options.secure as boolean) }, tokens);
  return seen;
}

describe("session cookies", () => {
  afterEach(() => vi.unstubAllEnvs());

  it("are Secure when the environment is unset or not local", () => {
    expect(secureFlags()).toEqual([true, true, true]);
    vi.stubEnv("IBH_ENVIRONMENT", "production");
    expect(secureFlags()).toEqual([true, true, true]);
  });

  it("are not Secure on the local stack, so a phone on the LAN address keeps its session", () => {
    vi.stubEnv("IBH_ENVIRONMENT", "local");
    expect(secureFlags()).toEqual([false, false, false]);
  });
});
