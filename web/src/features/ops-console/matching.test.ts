import { describe, expect, it } from "vitest";

import { canSend, isActive, move, SHORTLIST_MAX, toggleChoice } from "./matching";

describe("toggleChoice", () => {
  it("adds in order and takes a contractor off again", () => {
    expect(toggleChoice([], "a")).toEqual(["a"]);
    expect(toggleChoice(["a"], "b")).toEqual(["a", "b"]);
    expect(toggleChoice(["a", "b"], "a")).toEqual(["b"]);
  });

  it("stops at three", () => {
    const full = ["a", "b", "c"];
    expect(full).toHaveLength(SHORTLIST_MAX);
    expect(toggleChoice(full, "d")).toEqual(full);
    expect(toggleChoice(full, "b")).toEqual(["a", "c"]); // but a chosen one can still come off
  });
});

describe("canSend", () => {
  it("needs one to three", () => {
    expect(canSend([])).toBe(false);
    expect(canSend(["a"])).toBe(true);
    expect(canSend(["a", "b", "c"])).toBe(true);
    expect(canSend(["a", "b", "c", "d"])).toBe(false);
  });
});

describe("move", () => {
  it("changes the order the client sees", () => {
    expect(move(["a", "b", "c"], "b", -1)).toEqual(["b", "a", "c"]);
    expect(move(["a", "b", "c"], "b", 1)).toEqual(["a", "c", "b"]);
  });

  it("does nothing at the ends or for an unknown id", () => {
    expect(move(["a", "b"], "a", -1)).toEqual(["a", "b"]);
    expect(move(["a", "b"], "b", 1)).toEqual(["a", "b"]);
    expect(move(["a", "b"], "z", 1)).toEqual(["a", "b"]);
  });
});

describe("isActive", () => {
  it("is true only while nothing is decided", () => {
    expect(isActive("open")).toBe(true);
    expect(isActive("shortlisted")).toBe(true);
    expect(isActive("matched")).toBe(false);
    expect(isActive("cancelled")).toBe(false);
  });
});
