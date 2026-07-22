import { rm } from "node:fs/promises";
import { join } from "node:path";
import tailwindcss from "@tailwindcss/vite";
import { tanstackRouter } from "@tanstack/router-plugin/vite";
import react from "@vitejs/plugin-react";
import { defineConfig, loadEnv, type Plugin } from "vite";

/** The MSW worker lives in public/ for dev, but must never ship in a live build. */
function stripMockWorker(dataMode: string): Plugin {
  let outDir = "dist";
  return {
    name: "irrevon:strip-mock-worker",
    apply: "build",
    configResolved(config) {
      // Respect --outDir: a side build must never reach into another build's output.
      outDir = config.build.outDir;
    },
    async closeBundle() {
      if (dataMode !== "mock") {
        await rm(join(import.meta.dirname, outDir, "mockServiceWorker.js"), { force: true });
      }
    },
  };
}

// Mock mode is a dev/test/review capability only. A production build with
// VITE_IRREVON_DATA_MODE=mock is refused outright (BRIEF §3.2).
export default defineConfig(({ command, mode }) => {
  const env = loadEnv(mode, process.cwd(), "VITE_IRREVON_");
  const dataMode = env.VITE_IRREVON_DATA_MODE ?? (mode === "production" ? "live" : "mock");

  if (command === "build" && mode === "production" && dataMode === "mock") {
    throw new Error(
      "Refusing to build: mock data mode is not allowed in a production build. " +
        "Use `pnpm build:review` for a fixture-backed review build.",
    );
  }

  return {
    plugins: [
      tanstackRouter({
        target: "react",
        autoCodeSplitting: true,
        routesDirectory: "src/app/routes",
        generatedRouteTree: "src/app/routeTree.gen.ts",
      }),
      react(),
      tailwindcss(),
      stripMockWorker(dataMode),
    ],
    resolve: {
      alias: { "@": new URL("./src", import.meta.url).pathname },
    },
    define: {
      __IRREVON_DATA_MODE__: JSON.stringify(dataMode),
    },
    server: {
      port: 5199,
      strictPort: true,
      // `pnpm dev:live` only: proxy API reads to a local `irrevon serve`.
      // MSW dev (`pnpm dev`) is untouched — the proxy exists only when the
      // live env var is set, so mock mode never grows a network path.
      ...(command === "serve" && dataMode === "live"
        ? { proxy: { "/api": "http://127.0.0.1:5180" } }
        : {}),
    },
    preview: { port: 5199, strictPort: true },
    build: { sourcemap: false },
  };
});
