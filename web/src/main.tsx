import { RouterProvider } from "@tanstack/react-router";
import { StrictMode } from "react";
import { createRoot } from "react-dom/client";
import { Providers } from "./app/providers";
import { router } from "./app/router";
import "./styles.css";

async function start() {
  // Literal define comparison: the whole MSW chunk is eliminated from live builds.
  if (__DETENT_DATA_MODE__ === "mock") {
    const { worker } = await import("./mocks/browser");
    await worker.start({ onUnhandledRequest: "bypass", quiet: true });
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
