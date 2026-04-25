// Client-side facet filter for /food/ and /cocktails/ landing pages.
// Each filter group acts independently; multiple non-empty values across
// groups are combined with AND.

import { onReady } from "./util.js";

// Python-side keys use snake_case ("spirit_base"); HTML data-attrs are hyphenated
// ("data-spirit-base"); JS reads via dataset.spiritBase. Translate once.
function snakeToCamel(s: string): string {
  return s.replace(/_(\w)/g, (_, c) => c.toUpperCase());
}

function installFacets(): void {
  const rail = document.querySelector<HTMLElement>(".facet-rail");
  const grid = document.getElementById("facet-results");
  const countEl = document.getElementById("facet-count");
  if (!rail || !grid) return;

  const wrappers = Array.from(grid.querySelectorAll<HTMLElement>(".recipe-card-wrapper"));
  const filters = new Map<string, string>();

  const apply = () => {
    const active = [...filters.entries()].filter(([, v]) => v !== "");
    let visible = 0;
    wrappers.forEach((w) => {
      const matches = active.every(([facet, value]) => w.dataset[snakeToCamel(facet)] === value);
      w.style.display = matches ? "" : "none";
      if (matches) visible++;
    });
    if (countEl) {
      countEl.textContent = active.length === 0 ? "" : `${visible} of ${wrappers.length} recipes`;
    }
  };

  rail.querySelectorAll<HTMLButtonElement>(".facet-chip").forEach((chip) => {
    chip.addEventListener("click", () => {
      const facet = chip.dataset.facet || "";
      const value = chip.dataset.value || "";
      // Short-circuit: clicking the already-active chip is a no-op.
      if (filters.get(facet) === value) return;
      filters.set(facet, value);
      const group = chip.closest("fieldset");
      group?.querySelectorAll<HTMLButtonElement>(".facet-chip").forEach((c) => {
        c.classList.toggle("is-active", c === chip);
        c.setAttribute("aria-pressed", c === chip ? "true" : "false");
      });
      apply();
    });
    chip.setAttribute("aria-pressed", chip.classList.contains("is-active") ? "true" : "false");
  });
}

onReady(installFacets);
