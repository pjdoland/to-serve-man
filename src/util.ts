// Shared utilities and types for the TS bundle. All entry-point modules import
// from here so storage keys, store shapes, JSON load/save, DOM-ready handling,
// and HTML escaping have one source of truth.

export const STORAGE_KEYS = {
  scale: (slug: string) => `tsm:scale:${slug}`,
  units: "tsm:units",
  cookMode: (slug: string) => `tsm:cook:${slug}`,
  favorites: "tsm:favorites",
  notes: "tsm:notes",
  shoppingList: "tsm:shopping",
  recent: "tsm:recent",
};

export interface FavoritesStore { favorites: string[]; }
export interface NotesStore { [slug: string]: { date?: string; note?: string }[]; }
export interface ShoppingItem { recipeSlug: string; recipeTitle: string; text: string; checked: boolean; }
export interface ShoppingStore { items: ShoppingItem[]; }
export interface RecentEntry { slug: string; title: string; visitedAt: string; }
export interface RecentStore { recent: RecentEntry[]; }

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
