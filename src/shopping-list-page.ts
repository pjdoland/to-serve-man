// Renders the /shopping-list/ page from localStorage. Groups items by recipe so
// users can clear individual recipes from a multi-recipe weeknight plan, with
// an undo strip after destructive actions (no confirm prompts mid-cook).

import {
  type ShoppingItem,
  type ShoppingStore,
  STORAGE_KEYS,
  escapeHtml,
  loadJson,
  onReady,
  saveJson,
} from "./util.js";

const UNDO_MS = 10000;

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
  const undoStrip = document.getElementById("tsm-shop-undo");
  const undoText = document.getElementById("tsm-undo-text");
  const undoBtn = document.getElementById("tsm-undo-action");

  let undoTimer: number | null = null;
  // Stores the snapshot to restore + the human-readable label currently shown.
  // When a second destructive action lands within the undo window we KEEP the
  // earlier snapshot (it represents the older "true" state to roll back to).
  let pendingRestore: ShoppingStore | null = null;

  const showUndo = (label: string, prevStore: ShoppingStore) => {
    if (pendingRestore === null) pendingRestore = prevStore;
    if (undoText) undoText.textContent = label;
    undoStrip?.removeAttribute("hidden");
    if (undoTimer) clearTimeout(undoTimer);
    undoTimer = window.setTimeout(() => {
      undoStrip?.setAttribute("hidden", "");
      pendingRestore = null;
      undoTimer = null;
    }, UNDO_MS);
  };

  const renderTo = (target: HTMLElement) => {
    const store = load();
    if (!store.items.length) {
      empty?.removeAttribute("hidden");
      list?.setAttribute("hidden", "");
      return;
    }
    empty?.setAttribute("hidden", "");
    list?.removeAttribute("hidden");

    const groups: Record<string, { item: ShoppingItem; idx: number }[]> = {};
    store.items.forEach((item, idx) => {
      (groups[item.recipeTitle] ??= []).push({ item, idx });
    });

    target.innerHTML = Object.entries(groups).map(([title, entries]) => `
      <li class="mb-8" data-recipe="${escapeHtml(title)}">
        <header class="shop-recipe-header">
          <h3 class="font-serif text-xl m-0">${escapeHtml(title)}</h3>
          <button type="button" class="shop-remove-btn" data-clear-recipe="${escapeHtml(title)}" aria-label="Remove ${escapeHtml(title)} from list" title="Remove this recipe">×</button>
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
          const label = cb.parentElement?.querySelector("label");
          label?.classList.toggle("line-through", cb.checked);
          label?.classList.toggle("text-cookbook-light", cb.checked);
        }
      });
    });

    target.querySelectorAll<HTMLButtonElement>("[data-clear-recipe]").forEach((btn) => {
      btn.addEventListener("click", () => {
        // The dataset value is HTML-escaped (e.g. "Beef &amp; Beer"); decode it for
        // user-visible text and for the equality check against item.recipeTitle.
        const title = (() => {
          const tmp = document.createElement("textarea");
          tmp.innerHTML = btn.dataset.clearRecipe || "";
          return tmp.value;
        })();
        const prev = load();
        const next: ShoppingStore = { items: prev.items.filter((it) => it.recipeTitle !== title) };
        save(next);
        renderTo(target);
        showUndo(`Removed ${title}.`, prev);
      });
    });
  };

  if (ul) renderTo(ul);

  undoBtn?.addEventListener("click", () => {
    if (pendingRestore) {
      save(pendingRestore);
      pendingRestore = null;
      undoStrip?.setAttribute("hidden", "");
      if (undoTimer) clearTimeout(undoTimer);
      if (ul) renderTo(ul);
    }
  });

  document.getElementById("tsm-shop-clear")?.addEventListener("click", () => {
    const prev = load();
    if (!prev.items.length) return;
    save({ items: [] });
    if (ul) renderTo(ul);
    showUndo(`Cleared ${prev.items.length} items.`, prev);
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
