// Base-path-aware internal links (GitHub Pages project sites serve under /<repo>/).
const base = import.meta.env.BASE_URL.replace(/\/$/, "");

export const href = (path: string): string => `${base}${path}`;
export const asset = href;
