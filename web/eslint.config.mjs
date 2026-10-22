import { defineConfig, globalIgnores } from "eslint/config";
import nextVitals from "eslint-config-next/core-web-vitals";
import nextTs from "eslint-config-next/typescript";

// Folder rules from the Spec and ADR 0004: app/ holds routes only and may import anything;
// features/ and common/ never import from app/; common/ never imports from features/.
const fromApp = {
  group: ["@/app", "@/app/*", "**/app/*"],
  message: "Only app/ route files import from app/.",
};
const fromFeatures = {
  group: ["@/features", "@/features/*", "**/features/*"],
  message: "common/ is shared by every feature, so it cannot depend on one.",
};

export default defineConfig([
  ...nextVitals,
  ...nextTs,
  {
    files: ["src/features/**/*.{ts,tsx}"],
    rules: { "no-restricted-imports": ["error", { patterns: [fromApp] }] },
  },
  {
    files: ["src/common/**/*.{ts,tsx}"],
    rules: { "no-restricted-imports": ["error", { patterns: [fromApp, fromFeatures] }] },
  },
  globalIgnores([
    ".next/**",
    "out/**",
    "next-env.d.ts",
    "playwright-report/**",
    "test-results/**",
    "src/common/api/schema.d.ts",
  ]),
]);
