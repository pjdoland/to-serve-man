// Shared utilities for the TS bundle. All entry-point modules import from here
// to avoid duplicating storage keys, JSON load/save shape, DOM-ready handling,
// and HTML escaping (which several callers were doing via raw innerHTML).

export const STORAGE_KEYS = {
  scale: (slug: string) => `tsm:scale:${slug}`,
  units: "tsm:units",
  cookMode: (slug: string) => `tsm:cook:${slug}`,
  favorites: "tsm:favorites",
  notes: "tsm:notes",
  shoppingList: "tsm:shopping",
};

export function loadJson<T>(key: string, fallback: T): T {
  const raw = localStorage.getItem(key);
  if (!raw) return fallback;
  try {
    return JSON.parse(raw) as T;
  } catch {
    return fallback;
  }
}

export function saveJson<T>(key: string, value: T): void {
  localStorage.setItem(key, JSON.stringify(value));
}

export function onReady(fn: () => void): void {
  if (document.readyState === "loading") {
    document.addEventListener("DOMContentLoaded", fn);
  } else {
    fn();
  }
}

export function escapeHtml(text: string): string {
  const div = document.createElement("div");
  div.textContent = text;
  return div.innerHTML;
}
