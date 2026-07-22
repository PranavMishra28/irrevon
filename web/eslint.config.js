import pluginQuery from "@tanstack/eslint-plugin-query";
import pluginRouter from "@tanstack/eslint-plugin-router";
import boundaries from "eslint-plugin-boundaries";
import jsxA11y from "eslint-plugin-jsx-a11y";
import tseslint from "typescript-eslint";

/**
 * Everything is error or off — warn-level lint rots under agent-driven
 * development. Import boundaries mirror BRIEF §6; status-utility and
 * dark-variant bans are enforced here because feature code must not paint
 * status colors or fork themes.
 */

const statusUtilityBan = {
  selector: "Literal[value=/(?:bg|text|border|fill|stroke|decoration|outline|ring)-status-/]",
  message:
    "Status color utilities are restricted to src/shared/domain/status/**. Render a status through its taxonomy component instead.",
};

const darkVariantBan = {
  selector: "Literal[value=/\\bdark:/]",
  message: "No dark: variants — theming happens via tokens, never per-component overrides.",
};

const rawZIndexBan = {
  selector: "Literal[value=/\\bz-\\[/]",
  message: "Raw z-index values are banned; use the semantic --sys-z-* layer tokens.",
};

export default tseslint.config(
  {
    ignores: [
      "dist/**",
      "dist-live-guard/**",
      "dist-live-stub/**",
      "dist-mock-refused/**",
      "storybook-static/**",
      "node_modules/**",
      "src/app/routeTree.gen.ts",
      "src/shared/contracts/generated/**",
      "public/mockServiceWorker.js",
      ".dev-screens/**",
      "test-results/**",
      "playwright-report/**",
    ],
  },
  ...tseslint.configs.strictTypeChecked,
  ...tseslint.configs.stylisticTypeChecked,
  ...pluginQuery.configs["flat/recommended"],
  ...pluginRouter.configs["flat/recommended"],
  {
    languageOptions: {
      parserOptions: {
        projectService: {
          allowDefaultProject: ["eslint.config.js"],
        },
        tsconfigRootDir: import.meta.dirname,
      },
    },
    rules: {
      "@typescript-eslint/restrict-template-expressions": ["error", { allowNumber: true }],
      "@typescript-eslint/no-unused-vars": [
        "error",
        { argsIgnorePattern: "^_", varsIgnorePattern: "^_" },
      ],
    },
  },
  {
    files: ["src/**/*.{ts,tsx}"],
    plugins: { "jsx-a11y": jsxA11y, boundaries },
    settings: {
      "import/resolver": {
        typescript: { project: "./tsconfig.json" },
      },
      "boundaries/elements": [
        { type: "app", pattern: "src/app/**" },
        { type: "feature", pattern: "src/features/*/**", capture: ["feature"] },
        { type: "shared-domain", pattern: "src/shared/domain/**" },
        { type: "shared-api", pattern: "src/shared/api/**" },
        { type: "shared-contracts", pattern: "src/shared/contracts/**" },
        { type: "shared-ui", pattern: "src/shared/ui/**" },
        { type: "shared-lib", pattern: "src/shared/lib/**" },
        { type: "mocks", pattern: "src/mocks/**" },
        { type: "fixtures", pattern: "fixtures/**" },
      ],
      "boundaries/dependency-nodes": ["import", "dynamic-import"],
    },
    rules: {
      ...jsxA11y.flatConfigs.strict.rules,
      "boundaries/no-unknown-files": "error",
      "boundaries/no-unknown-dependencies": "error",
      "boundaries/dependencies": [
        "error",
        {
          default: "disallow",
          policies: [
            {
              from: { element: { type: "app" } },
              allow: [
                { element: { type: "app" } },
                { element: { type: "feature" } },
                { element: { type: "shared-domain" } },
                { element: { type: "shared-api" } },
                { element: { type: "shared-contracts" } },
                { element: { type: "shared-ui" } },
                { element: { type: "shared-lib" } },
              ],
            },
            // main.tsx and mocks wiring are covered by the boundaries-off override below.
            {
              from: { element: { type: "feature" } },
              allow: [
                { element: { type: "feature", feature: "{{from.feature}}" } },
                { element: { type: "shared-domain" } },
                { element: { type: "shared-api" } },
                { element: { type: "shared-contracts" } },
                { element: { type: "shared-ui" } },
                { element: { type: "shared-lib" } },
              ],
            },
            {
              from: { element: { type: "shared-domain" } },
              allow: [
                { element: { type: "shared-domain" } },
                { element: { type: "shared-contracts" } },
                { element: { type: "shared-ui" } },
                { element: { type: "shared-lib" } },
              ],
            },
            {
              from: { element: { type: "shared-api" } },
              allow: [
                { element: { type: "shared-api" } },
                { element: { type: "shared-contracts" } },
                { element: { type: "shared-lib" } },
              ],
            },
            {
              from: { element: { type: "shared-contracts" } },
              allow: [{ element: { type: "shared-contracts" } }],
            },
            {
              from: { element: { type: "shared-ui" } },
              allow: [{ element: { type: "shared-ui" } }, { element: { type: "shared-lib" } }],
            },
            {
              from: { element: { type: "shared-lib" } },
              allow: [{ element: { type: "shared-lib" } }],
            },
            {
              from: { element: { type: "mocks" } },
              allow: [
                { element: { type: "mocks" } },
                { element: { type: "shared-contracts" } },
                // envelope TYPES only; the fixture element is the sanctioned
                // mock data source — production code never imports fixtures
                { element: { type: "shared-api" } },
                { element: { type: "fixtures" } },
              ],
            },
          ],
        },
      ],
      "no-restricted-imports": [
        "error",
        {
          patterns: [
            {
              group: ["@base-ui/react", "@base-ui/react/*"],
              message: "Base UI is wrapped by src/shared/ui/primitives — import the primitive.",
            },
            {
              group: ["lucide-react"],
              message: "Icons come from the registry at @/shared/ui/icons.",
            },
            {
              group: ["radix-ui", "@radix-ui/*", "react-aria-components", "@headlessui/*"],
              message: "Base UI is the only behavior-primitive library.",
            },
          ],
        },
      ],
      "no-restricted-syntax": ["error", statusUtilityBan, darkVariantBan, rawZIndexBan],
      "@typescript-eslint/restrict-template-expressions": ["error", { allowNumber: true }],
    },
  },
  {
    files: ["src/app/routes/**"],
    rules: {
      // TanStack Router control flow: `throw redirect()` / `throw notFound()`.
      "@typescript-eslint/only-throw-error": "off",
    },
  },
  {
    files: ["src/features/effects/effects-grid.tsx"],
    rules: {
      // The WAI-ARIA APG grid pattern is a native <table role="grid"> with a
      // roving tabindex; jsx-a11y flags the role remap generically, axe passes it.
      "jsx-a11y/no-noninteractive-element-to-interactive-role": "off",
    },
  },
  {
    files: ["src/shared/ui/primitives/**"],
    rules: {
      "no-restricted-imports": [
        "error",
        {
          patterns: [
            {
              group: ["lucide-react"],
              message: "Icons come from the registry at @/shared/ui/icons.",
            },
            {
              group: ["radix-ui", "@radix-ui/*", "react-aria-components", "@headlessui/*"],
              message: "Base UI is the only behavior-primitive library.",
            },
          ],
        },
      ],
    },
  },
  {
    files: ["src/shared/ui/icons/**"],
    rules: {
      "no-restricted-imports": [
        "error",
        {
          patterns: [
            {
              group: ["@base-ui/react", "@base-ui/react/*"],
              message: "Base UI is wrapped by src/shared/ui/primitives — import the primitive.",
            },
          ],
        },
      ],
    },
  },
  {
    files: ["src/shared/domain/status/**"],
    rules: {
      // The taxonomy is the one sanctioned consumer of status utilities.
      "no-restricted-syntax": ["error", darkVariantBan, rawZIndexBan],
    },
  },
  {
    // main.tsx is the composition entry point: it wires app + mocks by design.
    files: [
      "src/main.tsx",
      "src/vite-env.d.ts",
      "**/*.stories.tsx",
      "**/*.test.ts",
      "**/*.test.tsx",
      "e2e/**",
      "scripts/**",
      ".storybook/**",
    ],
    rules: {
      "boundaries/dependencies": "off",
      "boundaries/no-unknown-files": "off",
      "boundaries/no-unknown-dependencies": "off",
    },
  },
  {
    files: ["**/*.js", "**/*.mjs"],
    ...tseslint.configs.disableTypeChecked,
  },
);
