import { readdirSync, readFileSync, statSync } from "node:fs";
import { join } from "node:path";
import { fileURLToPath } from "node:url";

import { describe, expect, it } from "vitest";

// The design rule "tokens, never hard-coded colours", enforced: no hex or rgb() colours and no Tailwind
// arbitrary values (bg-[#123456], text-[13px], ...) in the app's source. Values come from theme.css.

const SRC = fileURLToPath(new URL("../..", import.meta.url));

function files(dir: string): string[] {
  return readdirSync(dir).flatMap((name) => {
    const path = join(dir, name);
    if (statSync(path).isDirectory()) return files(path);
    return /\.(tsx?|css)$/.test(name) && !/\.test\.tsx?$/.test(name) ? [path] : [];
  });
}

const ALLOWED = new Set(["tokens.css"]); // the copy of the handoff's tokens: where the values live
const sources = files(SRC).filter((f) => !ALLOWED.has(f.split(/[\\/]/).pop() ?? ""));

describe("no raw styles in src/", () => {
  it("has no Tailwind arbitrary values or arbitrary variants", () => {
    const offenders = sources.filter((f) => {
      const text = readFileSync(f, "utf8");
      // bg-[#123456], text-[13px] ... and variants like [&>div]:flex or [@media(...)]:x
      return /\b[a-z][a-z0-9-]*-\[[^\]]+\]/.test(text) || /[\s"'`]\[[&@][^\]]*\]:/.test(text);
    });
    expect(offenders).toEqual([]);
  });

  it("never puts a breakpoint or state variant on a type-* style (they are plain classes, see theme.css)", () => {
    const offenders = sources.filter((f) => /[a-z-]+:type-[a-z-]+/.test(readFileSync(f, "utf8")));
    expect(offenders).toEqual([]);
  });

  it("has no hex, rgb() or hsl() colours", () => {
    const offenders = sources.filter((f) => {
      const text = readFileSync(f, "utf8").replace(/\/\*[\s\S]*?\*\/|\/\/.*$/gm, "");
      return /#[0-9a-fA-F]{3,8}\b(?![\w-])|\brgba?\(|\bhsla?\(/.test(text);
    });
    expect(offenders).toEqual([]);
  });
});
