import { afterEach, describe, expect, it, vi } from "vitest";

import { IdempotentAction, randomKey } from "./idempotency";

const UUID = /^[0-9a-f]{8}-[0-9a-f]{4}-4[0-9a-f]{3}-[89ab][0-9a-f]{3}-[0-9a-f]{12}$/;

describe("randomKey", () => {
  afterEach(() => vi.unstubAllGlobals());

  it("makes a UUID where crypto.randomUUID is missing (http on a LAN address)", () => {
    vi.stubGlobal("crypto", { getRandomValues: globalThis.crypto.getRandomValues.bind(globalThis.crypto) });
    const a = randomKey();
    expect(a).toMatch(UUID);
    expect(randomKey()).not.toBe(a);
  });

  it("uses crypto.randomUUID when it exists", () => {
    expect(randomKey()).toMatch(UUID);
  });
});

describe("IdempotentAction defaults", () => {
  it("can be created without a key maker and reuses the key for the same input", () => {
    const action = new IdempotentAction<{ a: number }>();
    expect(action.keyFor({ a: 1 })).toBe(action.keyFor({ a: 1 }));
  });
});
