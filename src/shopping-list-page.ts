export {}; // module isolation

// Renders the /shopping-list/ page from localStorage.

interface ShoppingItem { recipeSlug: string; recipeTitle: string; text: string; checked: boolean; }
interface ShoppingStore { items: ShoppingItem[]; }

function load(): ShoppingStore {
  return JSON.parse(localStorage.getItem("tsm:shopping") || '{"items":[]}');
}
function save(s: ShoppingStore): void {
  localStorage.setItem("tsm:shopping", JSON.stringify(s));
}

function init(): void {
  const empty = document.getElementById("tsm-shop-empty");
  const list = document.getElementById("tsm-shop-list");
  const ul = list?.querySelector("ul");

  const render = () => {
    const store = load();
    if (!store.items.length) {
      empty?.removeAttribute("hidden");
      list?.setAttribute("hidden", "");
      return;
    }
    empty?.setAttribute("hidden", "");
    list?.removeAttribute("hidden");

    // Group by recipe.
    const byRecipe: Record<string, ShoppingItem[]> = {};
    store.items.forEach((it, idx) => {
      (it as any).idx = idx;
      if (!byRecipe[it.recipeTitle]) byRecipe[it.recipeTitle] = [];
      byRecipe[it.recipeTitle].push(it);
    });

    if (!ul) return;
    ul.innerHTML = Object.entries(byRecipe).map(([title, items]) => `
      <li class="mb-8">
        <h3 class="font-serif text-xl mb-3">${title}</h3>
        <ul class="list-none p-0">
          ${items.map((it) => `<li class="flex items-start gap-3 py-1">
            <input type="checkbox" data-idx="${(it as any).idx}" ${it.checked ? "checked" : ""} class="mt-1.5">
            <span class="${it.checked ? "line-through text-cookbook-light" : ""}">${it.text}</span>
          </li>`).join("")}
        </ul>
      </li>
    `).join("");

    ul.querySelectorAll<HTMLInputElement>("input[type=checkbox]").forEach((cb) => {
      cb.addEventListener("change", () => {
        const store = load();
        const idx = parseInt(cb.dataset.idx || "-1");
        if (idx >= 0 && store.items[idx]) {
          store.items[idx].checked = cb.checked;
          save(store);
          render();
        }
      });
    });
  };

  document.getElementById("tsm-shop-clear")?.addEventListener("click", () => {
    if (confirm("Clear the entire shopping list?")) {
      save({ items: [] });
      render();
    }
  });
  document.getElementById("tsm-shop-print")?.addEventListener("click", () => window.print());

  render();
}

if (document.readyState === "loading") {
  document.addEventListener("DOMContentLoaded", init);
} else {
  init();
}
