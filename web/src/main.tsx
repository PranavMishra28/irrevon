import { RouterProvider } from "@tanstack/react-router";
import { StrictMode } from "react";
import { createRoot } from "react-dom/client";
import { isMockMode } from "./app/data-mode";
import { Providers } from "./app/providers";
import { router } from "./app/router";
import "./styles.css";

async function start() {
  if (isMockMode) {
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
