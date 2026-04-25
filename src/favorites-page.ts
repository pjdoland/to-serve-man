export {}; // module isolation

// Renders the /favorites/ page from localStorage.

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
  const favs: FavoritesStore = JSON.parse(localStorage.getItem("tsm:favorites") || '{"favorites":[]}');
  const notes: NotesStore = JSON.parse(localStorage.getItem("tsm:notes") || "{}");

  const empty = document.getElementById("tsm-favorites-empty");
  const favList = document.getElementById("tsm-favorites-list");
  const madeList = document.getElementById("tsm-made-list");

  const validFavs = favs.favorites.filter((s) => idx[s]);
  if (validFavs.length && favList) {
    empty?.setAttribute("hidden", "");
    favList.removeAttribute("hidden");
    const ul = favList.querySelector("ul")!;
    ul.innerHTML = validFavs.map((s) => `<li><a href="${idx[s].url}" class="block py-3 px-4 border border-cookbook-border rounded hover:border-cookbook-accent no-underline text-cookbook-text">${idx[s].title}</a></li>`).join("");
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
        const note = e.note ? ` — ${e.note}` : "";
        return `<div class="text-sm text-cookbook-light">${date}${note}</div>`;
      }).join("");
      return `<li class="mb-6"><a href="${r.url}" class="font-serif text-xl no-underline text-cookbook-text border-none">${r.title}</a>${items}</li>`;
    }).join("");
  }
}

if (document.readyState === "loading") {
  document.addEventListener("DOMContentLoaded", init);
} else {
  init();
}
