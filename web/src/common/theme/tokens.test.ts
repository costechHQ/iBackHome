import { readFileSync } from "node:fs";
import { fileURLToPath } from "node:url";

import { describe, expect, it } from "vitest";

const read = (rel: string) => readFileSync(fileURLToPath(new URL(rel, import.meta.url)), "utf8");

// The same transformation as scripts/sync-tokens.sh: no @font-face lines, no header comment, no blank lines.
const body = (css: string) =>
  css
    .replace(/\r/g, "")
    .replace(/^\/\*[\s\S]*?\*\/\n/, "")
    .split("\n")
    .filter((line) => line.trim() !== "" && !line.startsWith("@font-face"));

describe("design tokens", () => {
  it("are an exact copy of the handoff's tokens.css (run `bun run sync:tokens` if this fails)", () => {
    expect(body(read("./tokens.css"))).toEqual(
      body(read("../../../../Docs/design/01-design-system/tokens.css")),
    );
  });

  it("theme.css maps tokens without any literal colour", () => {
    const theme = read("./theme.css").replace(/\/\*[\s\S]*?\*\//g, "");
    expect(theme).not.toMatch(/#[0-9a-f]{3,8}\b/i);
    expect(theme).not.toMatch(/\brgba?\(|\bhsla?\(|\boklch\(/i);
  });
});
