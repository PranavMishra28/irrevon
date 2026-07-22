// Base-path-aware internal links. The site serves at the origin root (base "/",
// ADR-0027), so this is currently an identity helper — kept so every internal
// link stays base-safe by construction if a base path ever returns.
const base = import.meta.env.BASE_URL.replace(/\/$/, "");

export const href = (path: string): string => `${base}${path}`;
export const asset = href;
