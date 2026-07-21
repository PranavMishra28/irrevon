/**
 * Build-time data mode. "mock" is accepted only by dev/test/review builds;
 * a production build with mock mode selected is refused in vite.config.ts.
 * Mock never falls through to live; live never falls back to fixtures.
 *
 * __DETENT_DATA_MODE__ is a Vite define (a literal after build), so
 * mock-only code behind it is dead-code-eliminated from live bundles.
 */
export type DataMode = "mock" | "live";

export const dataMode: DataMode = __DETENT_DATA_MODE__ === "mock" ? "mock" : "live";

export const isMockMode = dataMode === "mock";
