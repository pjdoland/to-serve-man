// Renders the /favorites/ page from localStorage.

import { STORAGE_KEYS, escapeHtml, loadJson, onReady } from "./util.js";

interface RecipeIndexEntry { slug: string; title: string; url: string; }
interface FavoritesStore { favorites: string[]; }
interface NotesStore { [slug: string]: { date?: string; note?: string }[]; }

function readIndex(): Record<string, RecipeIndexEntry> {
  const el = document.getElementById("tsm-recipe-index");
  if (!el) return {};
  const arr: RecipeIndexEntry[] = JSON.parse(el.textContent || "[]");
  const out: Record<string, RecipeIndexEntry> = {};
  arr.forEach((r) => { out[r.slug] = r; });
  return out;
}

function init(): void {
  const idx = readIndex();
  const favs = loadJson<FavoritesStore>(STORAGE_KEYS.favorites, { favorites: [] });
  const notes = loadJson<NotesStore>(STORAGE_KEYS.notes, {});

  const empty = document.getElementById("tsm-favorites-empty");
  const favList = document.getElementById("tsm-favorites-list");
  const madeList = document.getElementById("tsm-made-list");

  const validFavs = favs.favorites.filter((s) => idx[s]);
  if (validFavs.length && favList) {
    empty?.setAttribute("hidden", "");
    favList.removeAttribute("hidden");
    const ul = favList.querySelector("ul")!;
    ul.innerHTML = validFavs.map((s) => `<li><a href="${escapeHtml(idx[s].url)}" class="block py-3 px-4 border border-cookbook-border rounded hover:border-cookbook-accent no-underline text-cookbook-text">${escapeHtml(idx[s].title)}</a></li>`).join("");
  }

  const madeEntries = Object.entries(notes).filter(([s]) => idx[s]);
  if (madeEntries.length && madeList) {
    empty?.setAttribute("hidden", "");
    madeList.removeAttribute("hidden");
    const ul = madeList.querySelector("ul")!;
    ul.innerHTML = madeEntries.map(([slug, entries]) => {
      const r = idx[slug];
      const items = entries.map((e) => {
        const date = e.date ? new Date(e.date).toLocaleDateString() : "";
        const note = e.note ? ` — ${escapeHtml(e.note)}` : "";
        return `<div class="text-sm text-cookbook-light">${escapeHtml(date)}${note}</div>`;
      }).join("");
      return `<li class="mb-6"><a href="${escapeHtml(r.url)}" class="font-serif text-xl no-underline text-cookbook-text border-none">${escapeHtml(r.title)}</a>${items}</li>`;
    }).join("");
  }
}

onReady(init);
