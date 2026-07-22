import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import { getDensity, getSingleKeyShortcutsEnabled, getTheme, setTheme } from "./prefs";

/**
 * Pre-rename storage migration: preferences written under the old
 * `detent.*` keys survive the rename — the first read copies the value to
 * the `irrevon.*` key and removes the legacy one (one-time, per key).
 */

class MemoryStorage {
  private store = new Map<string, string>();
  getItem(key: string): string | null {
    return this.store.get(key) ?? null;
  }
  setItem(key: string, value: string): void {
    this.store.set(key, value);
  }
  removeItem(key: string): void {
    this.store.delete(key);
  }
}

let storage: MemoryStorage;

beforeEach(() => {
  storage = new MemoryStorage();
  vi.stubGlobal("localStorage", storage);
  vi.stubGlobal("window", {
    matchMedia: () => ({ matches: false }),
  });
  vi.stubGlobal("document", {
    documentElement: { setAttribute: () => undefined },
  });
});

afterEach(() => {
  vi.unstubAllGlobals();
});

describe("legacy detent.* key migration", () => {
  it("migrates a legacy theme on first read and removes the old key", () => {
    storage.setItem("detent.theme", "dark");
    expect(getTheme()).toBe("dark");
    expect(storage.getItem("irrevon.theme")).toBe("dark");
    expect(storage.getItem("detent.theme")).toBeNull();
  });

  it("migrates density and the single-key-shortcut toggle", () => {
    storage.setItem("detent.density", "dense");
    storage.setItem("detent.single-key-shortcuts", "off");
    expect(getDensity()).toBe("dense");
    expect(getSingleKeyShortcutsEnabled()).toBe(false);
    expect(storage.getItem("irrevon.density")).toBe("dense");
    expect(storage.getItem("irrevon.single-key-shortcuts")).toBe("off");
    expect(storage.getItem("detent.density")).toBeNull();
    expect(storage.getItem("detent.single-key-shortcuts")).toBeNull();
  });

  it("prefers the new key when both exist (migration already happened)", () => {
    storage.setItem("irrevon.theme", "light");
    storage.setItem("detent.theme", "dark");
    expect(getTheme()).toBe("light");
    // The stale legacy key is left alone — only a first read migrates.
    expect(storage.getItem("detent.theme")).toBe("dark");
  });

  it("falls back to system preference when neither key exists", () => {
    expect(getTheme()).toBe("light");
  });

  it("writes land on the new key only", () => {
    setTheme("dark");
    expect(storage.getItem("irrevon.theme")).toBe("dark");
    expect(storage.getItem("detent.theme")).toBeNull();
  });
});
