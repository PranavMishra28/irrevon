/**
 * Build-time data mode. "mock" is accepted only by dev/test/review builds;
 * a production build with mock mode selected is refused in vite.config.ts.
 * Mock never falls through to live; live never falls back to fixtures.
 */
declare const __DETENT_DATA_MODE__: string;

export type DataMode = "mock" | "live";

export const dataMode: DataMode = __DETENT_DATA_MODE__ === "mock" ? "mock" : "live";

export const isMockMode = dataMode === "mock";
