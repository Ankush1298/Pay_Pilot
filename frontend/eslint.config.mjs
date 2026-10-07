import { defineConfig, globalIgnores } from "eslint/config";
import nextVitals from "eslint-config-next/core-web-vitals";
import nextTs from "eslint-config-next/typescript";

const eslintConfig = defineConfig([
  ...nextVitals,
  ...nextTs,
  {
    rules: {
      // API payloads are untyped JSON for now; typing them is tracked as a recommendation in the audit report.
      "@typescript-eslint/no-explicit-any": "off",
      // Pages load their data from the API in an effect on purpose.
      "react-hooks/set-state-in-effect": "off",
    },
  },
  // Override default ignores of eslint-config-next.
  globalIgnores([
    // Default ignores of eslint-config-next:
    ".next/**",
    "out/**",
    "build/**",
    "next-env.d.ts",
    // macOS AppleDouble files created on non-HFS volumes
    "**/._*",
  ]),
]);

export default eslintConfig;
