/**
 * Persisted local preferences: theme, density, and the single-character
 * shortcut toggle (WCAG 2.1.4 requires single-key shortcuts to be
 * user-disableable). localStorage only — no telemetry, nothing leaves the machine.
 */

export type Theme = "light" | "dark";
export type Density = "comfortable" | "dense";

const THEME_KEY = "irrevon.theme";
const DENSITY_KEY = "irrevon.density";
const SINGLE_KEYS_KEY = "irrevon.single-key-shortcuts";

function read(key: string): string | null {
  try {
    return localStorage.getItem(key);
  } catch {
    return null;
  }
}

function write(key: string, value: string): void {
  try {
    localStorage.setItem(key, value);
  } catch {
    // Storage unavailable (private mode); preference lives for the session only.
  }
}

export function getTheme(): Theme {
  const stored = read(THEME_KEY);
  if (stored === "dark" || stored === "light") return stored;
  return window.matchMedia("(prefers-color-scheme: dark)").matches ? "dark" : "light";
}

export function setTheme(theme: Theme): void {
  document.documentElement.setAttribute("data-theme", theme);
  write(THEME_KEY, theme);
}

export function getDensity(): Density {
  const stored = read(DENSITY_KEY);
  return stored === "dense" ? "dense" : "comfortable";
}

export function setDensity(density: Density): void {
  document.documentElement.setAttribute("data-density", density);
  write(DENSITY_KEY, density);
}

export function getSingleKeyShortcutsEnabled(): boolean {
  return read(SINGLE_KEYS_KEY) !== "off";
}

export function setSingleKeyShortcutsEnabled(enabled: boolean): void {
  write(SINGLE_KEYS_KEY, enabled ? "on" : "off");
}
