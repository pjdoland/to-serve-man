// Client-side facet filter for /food/ and /cocktails/ landings.
// Two control modes per facet:
//   - "pills"    (≤7 options): single-value chip selection
//   - "dropdown" (>7 options): multi-select checkbox list inside <details>
// All non-empty filters are AND-combined across groups; values within one
// dropdown group are OR-combined (same vocabulary, multi-select).

import { onReady } from "./util.js";

function snakeToCamel(s: string): string {
  return s.replace(/_(\w)/g, (_, c) => c.toUpperCase());
}

function installFacets(): void {
  const rail = document.querySelector<HTMLElement>(".facet-rail");
  const grid = document.getElementById("facet-results");
  const countEl = document.getElementById("facet-count");
  const clearBtn = document.getElementById("facet-clear");
  if (!rail || !grid) return;

  const wrappers = Array.from(grid.querySelectorAll<HTMLElement>(".recipe-card-wrapper"));
  // facet → set of selected values (empty set = no filter on that facet)
  const filters = new Map<string, Set<string>>();

  // Track previous visibility so we only write to the DOM when it changes.
  const prevVisible = new WeakSet<HTMLElement>(wrappers);

  const apply = () => {
    // Pre-compute camelCase keys once per call, not once per card per facet.
    const active: [string, Set<string>][] = [...filters.entries()]
      .filter(([, vs]) => vs.size > 0)
      .map(([k, vs]) => [snakeToCamel(k), vs]);
    let visible = 0;
    wrappers.forEach((w) => {
      const matches = active.every(([key, values]) => values.has(w.dataset[key] || ""));
      const wasVisible = prevVisible.has(w);
      if (matches !== wasVisible) {
        w.style.display = matches ? "" : "none";
        if (matches) prevVisible.add(w);
        else prevVisible.delete(w);
      }
      if (matches) visible++;
    });
    if (countEl) {
      countEl.textContent = active.length === 0 ? "" : `${visible} of ${wrappers.length} recipes`;
    }
    clearBtn?.toggleAttribute("hidden", active.length === 0);
  };

  // Pills: single-value-per-group (clicking another value replaces; clicking
  // the same value deselects).
  rail.querySelectorAll<HTMLButtonElement>(".facet-chip").forEach((chip) => {
    chip.addEventListener("click", () => {
      const facet = chip.dataset.facet || "";
      const value = chip.dataset.value || "";
      const set = filters.get(facet) ?? new Set<string>();
      const wasActive = set.has(value);
      set.clear();
      if (!wasActive) set.add(value);
      filters.set(facet, set);
      const group = chip.closest("fieldset");
      group?.querySelectorAll<HTMLButtonElement>(".facet-chip").forEach((c) => {
        const isActive = c === chip && !wasActive;
        c.classList.toggle("is-active", isActive);
        c.setAttribute("aria-pressed", isActive ? "true" : "false");
      });
      apply();
    });
  });

  // Dropdown mode: checkbox toggles add/remove from the value set.
  rail.querySelectorAll<HTMLInputElement>(".facet-dropdown-option input").forEach((cb) => {
    cb.addEventListener("change", () => {
      const facet = cb.dataset.facet || "";
      const value = cb.dataset.value || "";
      const set = filters.get(facet) ?? new Set<string>();
      if (cb.checked) set.add(value);
      else set.delete(value);
      filters.set(facet, set);

      const trigger = cb.closest("fieldset")?.querySelector<HTMLElement>(".facet-dropdown-label");
      if (trigger) {
        trigger.textContent = set.size === 0 ? "Any" : `${set.size} selected`;
      }
      apply();
    });
  });

  // Close any open facet dropdown when the user clicks outside it.
  document.addEventListener("click", (e) => {
    const target = e.target as Element;
    rail.querySelectorAll<HTMLDetailsElement>("details.facet-dropdown[open]").forEach((d) => {
      if (!d.contains(target)) d.removeAttribute("open");
    });
  });

  clearBtn?.addEventListener("click", () => {
    filters.clear();
    rail.querySelectorAll<HTMLButtonElement>(".facet-chip.is-active").forEach((c) => {
      c.classList.remove("is-active");
      c.setAttribute("aria-pressed", "false");
    });
    rail.querySelectorAll<HTMLInputElement>(".facet-dropdown-option input:checked").forEach((cb) => {
      cb.checked = false;
    });
    rail.querySelectorAll<HTMLElement>(".facet-dropdown-label").forEach((l) => {
      l.textContent = "Any";
    });
    apply();
  });
}

onReady(installFacets);
