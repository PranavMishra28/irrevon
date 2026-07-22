import { RouterProvider } from "@tanstack/react-router";
import { StrictMode } from "react";
import { createRoot } from "react-dom/client";
import { Providers } from "./app/providers";
import { router } from "./app/router";
import "./styles.css";

async function start() {
  // Literal define comparison: the whole MSW chunk is eliminated from live builds.
  if (__IRREVON_DATA_MODE__ === "mock") {
    try {
      const { worker } = await import("./mocks/browser");
      await worker.start({ onUnhandledRequest: "bypass", quiet: true });
    } catch (error) {
      // A blocked/unavailable service worker must not blank the app: reads
      // fail visibly per-surface instead (also how fault-injection E2E runs).
      console.warn("Mock worker unavailable; reads will fail visibly.", error);
    }
  }

  const rootElement = document.getElementById("root");
  if (!rootElement) throw new Error("#root not found");

  createRoot(rootElement).render(
    <StrictMode>
      <Providers>
        <RouterProvider router={router} />
      </Providers>
    </StrictMode>,
  );
}

void start();
