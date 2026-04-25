// Renders the /shopping-list/ page from localStorage. Groups items by recipe so
// users can clear individual recipes from a multi-recipe weeknight plan.

import {
  type ShoppingItem,
  type ShoppingStore,
  STORAGE_KEYS,
  escapeHtml,
  loadJson,
  onReady,
  saveJson,
} from "./util.js";

function load(): ShoppingStore {
  return loadJson<ShoppingStore>(STORAGE_KEYS.shoppingList, { items: [] });
}
function save(s: ShoppingStore): void {
  saveJson(STORAGE_KEYS.shoppingList, s);
}

function init(): void {
  const empty = document.getElementById("tsm-shop-empty");
  const list = document.getElementById("tsm-shop-list");
  const ul = list?.querySelector("ul");

  const renderTo = (target: HTMLElement) => {
    const store = load();
    if (!store.items.length) {
      empty?.removeAttribute("hidden");
      list?.setAttribute("hidden", "");
      return;
    }
    empty?.setAttribute("hidden", "");
    list?.removeAttribute("hidden");

    // Group, preserving original index so checkbox toggles know what to update.
    const groups: Record<string, { item: ShoppingItem; idx: number }[]> = {};
    store.items.forEach((item, idx) => {
      (groups[item.recipeTitle] ??= []).push({ item, idx });
    });

    target.innerHTML = Object.entries(groups).map(([title, entries]) => `
      <li class="mb-8" data-recipe="${escapeHtml(title)}">
        <header class="flex justify-between items-baseline mb-3">
          <h3 class="font-serif text-xl m-0">${escapeHtml(title)}</h3>
          <button type="button" class="tsm-btn" data-clear-recipe="${escapeHtml(title)}">Remove</button>
        </header>
        <ul class="list-none p-0">
          ${entries.map(({ item, idx }) => `<li class="flex items-start gap-3 py-1">
            <input type="checkbox" id="tsm-shop-${idx}" data-idx="${idx}" ${item.checked ? "checked" : ""} class="mt-1.5">
            <label for="tsm-shop-${idx}" class="${item.checked ? "line-through text-cookbook-light" : ""}">${escapeHtml(item.text)}</label>
          </li>`).join("")}
        </ul>
      </li>
    `).join("");

    target.querySelectorAll<HTMLInputElement>("input[type=checkbox]").forEach((cb) => {
      cb.addEventListener("change", () => {
        const current = load();
        const idx = parseInt(cb.dataset.idx || "-1");
        if (idx >= 0 && current.items[idx]) {
          current.items[idx].checked = cb.checked;
          save(current);
          // Toggle in place — no full re-render needed.
          const label = cb.parentElement?.querySelector("label");
          label?.classList.toggle("line-through", cb.checked);
          label?.classList.toggle("text-cookbook-light", cb.checked);
        }
      });
    });

    target.querySelectorAll<HTMLButtonElement>("[data-clear-recipe]").forEach((btn) => {
      btn.addEventListener("click", () => {
        const title = btn.dataset.clearRecipe;
        const current = load();
        current.items = current.items.filter((it) => it.recipeTitle !== title);
        save(current);
        renderTo(target);
      });
    });
  };

  if (ul) renderTo(ul);

  document.getElementById("tsm-shop-clear")?.addEventListener("click", () => {
    if (confirm("Clear the entire shopping list?")) {
      save({ items: [] });
      if (ul) renderTo(ul);
    }
  });
  document.getElementById("tsm-shop-print")?.addEventListener("click", () => window.print());
  document.getElementById("tsm-shop-copy")?.addEventListener("click", async () => {
    const store = load();
    const lines: string[] = [];
    const groups: Record<string, ShoppingItem[]> = {};
    store.items.forEach((it) => { (groups[it.recipeTitle] ??= []).push(it); });
    for (const [title, items] of Object.entries(groups)) {
      lines.push(title);
      items.forEach((i) => lines.push(`  ${i.checked ? "[x]" : "[ ]"} ${i.text}`));
      lines.push("");
    }
    try {
      await navigator.clipboard.writeText(lines.join("\n"));
      const btn = document.getElementById("tsm-shop-copy");
      if (btn) {
        const orig = btn.textContent;
        btn.textContent = "Copied!";
        setTimeout(() => { btn.textContent = orig; }, 1500);
      }
    } catch {
      alert("Couldn't copy to clipboard.");
    }
  });
}

onReady(init);
