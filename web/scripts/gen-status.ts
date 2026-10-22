// Regenerates src/common/status/registry.generated.ts from the handoff's state-to-ui.md.
// Run from web/: `bun run gen:status`.
import { readFileSync, writeFileSync } from "node:fs";
import { fileURLToPath } from "node:url";

import { parseStateToUi, renderRegistry } from "../src/common/status/parse";

const doc = fileURLToPath(new URL("../../Docs/design/04-api-mapping/state-to-ui.md", import.meta.url));
const out = fileURLToPath(new URL("../src/common/status/registry.generated.ts", import.meta.url));

writeFileSync(out, renderRegistry(parseStateToUi(readFileSync(doc, "utf8"))));
console.log(`wrote ${out}`);
