import { mkdir, mkdtemp, writeFile } from "node:fs/promises";
import { tmpdir } from "node:os";
import path from "node:path";

import { describe, expect, it } from "vitest";

import { readLegal } from "./legal";

describe("legal documents", () => {
  it("reads the Markdown file, and treats a missing or blank one as not supplied", async () => {
    const root = await mkdtemp(path.join(tmpdir(), "ibh-legal-"));
    expect(await readLegal("privacy", root)).toBeNull();
    await mkdir(path.join(root, "content", "legal"), { recursive: true });
    await writeFile(path.join(root, "content", "legal", "privacy.md"), "# Privacy\n\nText.\n");
    await writeFile(path.join(root, "content", "legal", "terms.md"), "  \n");
    expect(await readLegal("privacy", root)).toContain("# Privacy");
    expect(await readLegal("terms", root)).toBeNull();
  });

  it("isn't supplied in the repo yet, so both pages say they're being finalised", async () => {
    expect(await readLegal("privacy")).toBeNull();
    expect(await readLegal("terms")).toBeNull();
  });
});
