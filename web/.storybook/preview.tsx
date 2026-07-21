import type { Decorator, Preview } from "@storybook/react-vite";
import { LiveRegionProvider } from "../src/shared/ui/layout/live-regions";
import "../src/styles.css";

/**
 * Theme and density ride on document-element attributes exactly as in the
 * app; stories are captured in both themes/densities via toolbar globals.
 * axe violations are errors — never downgraded to pass a gate.
 */
const withThemeAndDensity: Decorator = (Story, context) => {
  const theme = (context.globals.theme as string | undefined) ?? "light";
  const density = (context.globals.density as string | undefined) ?? "comfortable";
  document.documentElement.setAttribute("data-theme", theme);
  document.documentElement.setAttribute("data-density", density);
  document.body.style.backgroundColor = "var(--color-canvas)";
  return <LiveRegionProvider>{Story()}</LiveRegionProvider>;
};

const preview: Preview = {
  decorators: [withThemeAndDensity],
  globalTypes: {
    theme: {
      description: "Color theme",
      toolbar: { title: "Theme", items: ["light", "dark"], dynamicTitle: true },
    },
    density: {
      description: "Data density",
      toolbar: { title: "Density", items: ["comfortable", "dense"], dynamicTitle: true },
    },
  },
  initialGlobals: { theme: "light", density: "comfortable" },
  parameters: {
    a11y: {
      test: "error",
      config: {},
      options: {},
    },
    controls: { expanded: true },
  },
};

export default preview;
