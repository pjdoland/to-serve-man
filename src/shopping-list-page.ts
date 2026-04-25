// Renders the /shopping-list/ page from localStorage.

import { STORAGE_KEYS, escapeHtml, loadJson, onReady, saveJson } from "./util.js";

interface ShoppingItem { recipeSlug: string; recipeTitle: string; text: string; checked: boolean; }
interface ShoppingStore { items: ShoppingItem[]; }

function init(): void {
  const empty = document.getElementById("tsm-shop-empty");
  const list = document.getElementById("tsm-shop-list");
  const ul = list?.querySelector("ul");

  const render = () => {
    const store = loadJson<ShoppingStore>(STORAGE_KEYS.shoppingList, { items: [] });
    if (!store.items.length) {
      empty?.removeAttribute("hidden");
      list?.setAttribute("hidden", "");
      return;
    }
    empty?.setAttribute("hidden", "");
    list?.removeAttribute("hidden");

    // Group by recipe; carry the original index alongside the item so the toggle handler
    // doesn't have to mutate the persisted item with a stray `idx` key.
    const byRecipe: Record<string, { item: ShoppingItem; idx: number }[]> = {};
    store.items.forEach((item, idx) => {
      (byRecipe[item.recipeTitle] ??= []).push({ item, idx });
    });

    if (!ul) return;
    ul.innerHTML = Object.entries(byRecipe).map(([title, entries]) => `
      <li class="mb-8">
        <h3 class="font-serif text-xl mb-3">${escapeHtml(title)}</h3>
        <ul class="list-none p-0">
          ${entries.map(({ item, idx }) => `<li class="flex items-start gap-3 py-1">
            <input type="checkbox" data-idx="${idx}" ${item.checked ? "checked" : ""} class="mt-1.5">
            <span class="${item.checked ? "line-through text-cookbook-light" : ""}">${escapeHtml(item.text)}</span>
          </li>`).join("")}
        </ul>
      </li>
    `).join("");

    ul.querySelectorAll<HTMLInputElement>("input[type=checkbox]").forEach((cb) => {
      cb.addEventListener("change", () => {
        const current = loadJson<ShoppingStore>(STORAGE_KEYS.shoppingList, { items: [] });
        const idx = parseInt(cb.dataset.idx || "-1");
        if (idx >= 0 && current.items[idx]) {
          current.items[idx].checked = cb.checked;
          saveJson(STORAGE_KEYS.shoppingList, current);
          // Toggle in place — no full re-render needed.
          const span = cb.parentElement?.querySelector("span");
          span?.classList.toggle("line-through", cb.checked);
          span?.classList.toggle("text-cookbook-light", cb.checked);
        }
      });
    });
  };

  document.getElementById("tsm-shop-clear")?.addEventListener("click", () => {
    if (confirm("Clear the entire shopping list?")) {
      saveJson(STORAGE_KEYS.shoppingList, { items: [] });
      render();
    }
  });
  document.getElementById("tsm-shop-print")?.addEventListener("click", () => window.print());

  render();
}

onReady(init);
