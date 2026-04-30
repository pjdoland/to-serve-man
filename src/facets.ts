// Client-side facet filter for /food/ and /cocktails/ landings.
// Each facet renders as a multi-select dropdown (<details> + checkboxes).
// All non-empty filters are AND-combined across groups; values within one
// group are OR-combined (same vocabulary, multi-select).

import { onReady } from "./util.js";

function snakeToCamel(s: string): string {
  return s.replace(/_(\w)/g, (_, c) => c.toUpperCase());
}

// Show selected values in the trigger up to this many; past that, fall back
// to a count so the trigger doesn't grow unboundedly wide.
const MAX_INLINE_SELECTIONS = 2;

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

  const updateLabel = (fieldset: HTMLElement) => {
    const trigger = fieldset.querySelector<HTMLElement>(".facet-dropdown-label");
    if (!trigger) return;
    const checked = Array.from(
      fieldset.querySelectorAll<HTMLInputElement>(".facet-dropdown-option input:checked"),
    );
    if (checked.length === 0) {
      trigger.textContent = "Any";
    } else if (checked.length <= MAX_INLINE_SELECTIONS) {
      // Use the visible <span> next to the checkbox so we get the title-cased
      // label as authored in the template, not the raw data-value.
      trigger.textContent = checked
        .map((cb) => cb.parentElement?.querySelector("span")?.textContent?.trim() || cb.dataset.value || "")
        .join(", ");
    } else {
      trigger.textContent = `${checked.length} selected`;
    }
  };

  rail.querySelectorAll<HTMLInputElement>(".facet-dropdown-option input").forEach((cb) => {
    cb.addEventListener("change", () => {
      const facet = cb.dataset.facet || "";
      const value = cb.dataset.value || "";
      const set = filters.get(facet) ?? new Set<string>();
      if (cb.checked) set.add(value);
      else set.delete(value);
      filters.set(facet, set);

      const fieldset = cb.closest<HTMLElement>("fieldset");
      if (fieldset) updateLabel(fieldset);
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
