import type { RequestHandler } from "msw";

/**
 * MSW is the only mock transport. Handlers stay empty until the
 * POST-integration schemas exist — fixtures are generated from those schemas,
 * never invented here (BRIEF §13.1).
 */
export const handlers: RequestHandler[] = [];
