import type { StorybookConfig } from "@storybook/react-vite";

const config: StorybookConfig = {
  stories: ["../src/**/*.stories.tsx"],
  addons: ["@storybook/addon-a11y", "@storybook/addon-vitest"],
  framework: "@storybook/react-vite",
  // Zero-telemetry posture: nothing leaves this machine.
  core: { disableTelemetry: true, disableWhatsNewNotifications: true },
};

export default config;
