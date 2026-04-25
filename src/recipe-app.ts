// Recipe page client app: cook view (wake-lock + sticky toolbar + drawer + checkboxes),
// timers, scaling, units, favorites, shopping list, sticky drawer, print card.
// Toolbar buttons are server-rendered in templates/recipe.html — this module only
// wires up handlers and toggles state. Each feature self-installs only when its
// DOM markers are present so the file stays one network round-trip.

import {
  type FavoritesStore,
  type NotesStore,
  type RecentStore,
  type ShoppingStore,
  STORAGE_KEYS,
  loadJson,
  onReady,
  saveJson,
} from "./util.js";

const RECENT_LIMIT = 8;
const RECENT_DEDUPE_MS = 5 * 60 * 1000; // skip re-recording the same recipe within 5 min

const article = document.querySelector<HTMLElement>("article[data-recipe-slug]");
const RECIPE_SLUG = article?.dataset.recipeSlug || "";
const RECIPE_TITLE = article?.dataset.recipeTitle || "";

function smartFraction(v: number): string {
  if (Number.isInteger(v)) return v.toString();
  const FRACTIONS: Record<string, string> = {
    "0.125": "⅛", "0.25": "¼", "0.333": "⅓", "0.375": "⅜",
    "0.5": "½", "0.625": "⅝", "0.667": "⅔", "0.75": "¾", "0.875": "⅞",
  };
  const whole = Math.floor(v);
  const frac = v - whole;
  for (const [k, glyph] of Object.entries(FRACTIONS)) {
    if (Math.abs(frac - parseFloat(k)) < 0.02) {
      return whole > 0 ? `${whole}${glyph}` : glyph;
    }
  }
  return v.toFixed(2).replace(/\.?0+$/, "");
}

function parseAmount(raw: string): number | null {
  const trimmed = raw.trim();
  if (/^\d+\/\d+$/.test(trimmed)) {
    const [n, d] = trimmed.split("/").map(Number);
    return d ? n / d : null;
  }
  const mixed = trimmed.match(/^(\d+)\s+(\d+)\/(\d+)$/);
  if (mixed) {
    const [, w, n, d] = mixed;
    return parseInt(w) + parseInt(n) / parseInt(d);
  }
  const f = parseFloat(trimmed);
  return Number.isNaN(f) ? null : f;
}

// --- Scaling -----------------------------------------------------------------

function installScaling(): void {
  const buttons = Array.from(document.querySelectorAll<HTMLButtonElement>('[data-action="scale"]'));
  const ingItems = Array.from(document.querySelectorAll<HTMLElement>(".ingredients-list li"));
  if (!buttons.length || !ingItems.length) return;

  const slug = RECIPE_SLUG;
  const saved = parseFloat(sessionStorage.getItem(STORAGE_KEYS.scale(slug)) || "1");
  let factor = saved || 1;

  const syncButtons = () => {
    buttons.forEach((b) => {
      b.classList.toggle("is-active", parseFloat(b.dataset.factor || "1") === factor);
    });
  };

  const apply = () => {
    sessionStorage.setItem(STORAGE_KEYS.scale(slug), factor.toString());
    document.body.classList.toggle("is-scaled", factor !== 1);

    ingItems.forEach((li) => {
      // Idempotent cache — first apply stamps origHtml; later applies reuse it.
      if (li.dataset.origHtml === undefined) li.dataset.origHtml = li.innerHTML;
      const orig = li.dataset.origHtml;
      // Recipes like "5 cups, 22 1/2 oz" carry parallel measurements — scale every number.
      li.innerHTML = orig.replace(/\(([^)]+)\)/, (full, body) => {
        const bare = body.trim().match(/^\d+(?:\.\d+)?$/);
        if (bare) return `(${Math.max(1, Math.round(parseFloat(bare[0]) * factor))})`;
        const NUMBER_RE = /\d+\s+\d+\/\d+|\d+\/\d+|\d+(?:\.\d+)?/g;
        return `(${body.replace(NUMBER_RE, (m: string) => {
          const amt = parseAmount(m);
          return amt === null ? m : smartFraction(amt * factor);
        })})`;
      });
    });

    syncButtons();
  };

  buttons.forEach((btn) => btn.addEventListener("click", () => {
    factor = parseFloat(btn.dataset.factor || "1");
    apply();
  }));
  // Boot: only re-render when a non-1 scale was carried over. Default factor
  // means the SSR'd ingredient HTML is already correct — just light up 1×.
  if (factor !== 1) apply();
  else syncButtons();
}

// --- Units (US ↔ metric, temperatures only) ----------------------------------

const PAIRED_F_C = /(\d+(?:\.\d+)?)\s*°\s*F\s*\(\s*(\d+(?:\.\d+)?)\s*°\s*C\s*\)/gi;
const PAIRED_C_F = /(\d+(?:\.\d+)?)\s*°\s*C\s*\(\s*(\d+(?:\.\d+)?)\s*°\s*F\s*\)/gi;
const STANDALONE_F = /(\d+(?:\.\d+)?)\s*°\s*F\b/gi;
const STANDALONE_C = /(\d+(?:\.\d+)?)\s*°\s*C\b/gi;

function installUnits(): void {
  const stepLis = Array.from(document.querySelectorAll<HTMLElement>(".instructions-list li"));
  const hasTemps = stepLis.some((li) => /\d+\s*°\s*[FC]/i.test(li.textContent || ""));
  const tool = document.querySelector<HTMLElement>('[data-feature="units"]');
  if (!tool || !hasTemps) return; // leave the SSR'd shell hidden when there's nothing to convert

  tool.removeAttribute("hidden");
  const buttons = Array.from(tool.querySelectorAll<HTMLButtonElement>("button"));
  let metric = localStorage.getItem(STORAGE_KEYS.units) === "metric";

  const apply = () => {
    document.body.classList.toggle("is-metric", metric);
    stepLis.forEach((li) => {
      if (li.dataset.origHtmlUnits === undefined) li.dataset.origHtmlUnits = li.innerHTML;
      let html = li.dataset.origHtmlUnits;
      // Recipes commonly carry both units in parallel ("375°F (190°C)") — collapse
      // to a single measurement matching the user's preference. Reset every apply()
      // because origHtmlUnits is the always-paired source of truth.
      html = html.replace(PAIRED_F_C, (_full, f, c) => (metric ? `${c}°C` : `${f}°F`));
      html = html.replace(PAIRED_C_F, (_full, c, f) => (metric ? `${c}°C` : `${f}°F`));
      // Anything still standalone gets converted on the fly.
      html = html.replace(STANDALONE_F, (full, n) =>
        metric ? `${Math.round((parseFloat(n) - 32) * 5 / 9)}°C` : full,
      );
      html = html.replace(STANDALONE_C, (full, n) =>
        metric ? full : `${Math.round(parseFloat(n) * 9 / 5 + 32)}°F`,
      );
      li.innerHTML = html;
    });
    buttons.forEach((b) => {
      const isActive = (b.dataset.units === "metric") === metric;
      b.classList.toggle("is-active", isActive);
      b.setAttribute("aria-pressed", isActive ? "true" : "false");
    });
  };

  buttons.forEach((btn) => btn.addEventListener("click", () => {
    metric = btn.dataset.units === "metric";
    localStorage.setItem(STORAGE_KEYS.units, metric ? "metric" : "us");
    apply();
  }));
  // Always run on boot so paired temps collapse to the chosen single unit.
  apply();
}

// --- Timers ------------------------------------------------------------------

const TIMER_UNIT_SECONDS: Record<string, number> = {
  second: 1, seconds: 1, sec: 1, secs: 1, s: 1,
  minute: 60, minutes: 60, min: 60, mins: 60, m: 60,
  hour: 3600, hours: 3600, hr: 3600, hrs: 3600, h: 3600,
};

function installTimers(): void {
  // Renderer emits <button class="timer">; promote handlers + accessible status.
  const timers = Array.from(document.querySelectorAll<HTMLButtonElement>("button.timer[data-value]"));
  if (!timers.length) return;

  const running = new Map<HTMLElement, number>();

  const beep = () => {
    const Ctx = window.AudioContext || window.webkitAudioContext;
    if (Ctx) {
      try {
        const ctx = new Ctx();
        const osc = ctx.createOscillator();
        const gain = ctx.createGain();
        osc.connect(gain); gain.connect(ctx.destination);
        osc.frequency.value = 880; gain.gain.value = 0.2;
        osc.start();
        setTimeout(() => { osc.stop(); ctx.close(); }, 800);
      } catch { /* audio unavailable */ }
    }
    navigator.vibrate?.([200, 100, 200]);
  };

  timers.forEach((el) => {
    const value = parseFloat(el.dataset.value || "0");
    const unit = (el.dataset.unit || "minutes").toLowerCase().split(/\s+/)[0];
    const seconds = Math.round(value * (TIMER_UNIT_SECONDS[unit] || 60));
    if (!seconds) return;

    el.addEventListener("click", () => {
      if (running.has(el)) return;
      let remaining = seconds;
      const original = el.textContent;
      el.classList.add("is-running");
      const tick = () => {
        remaining--;
        const m = Math.floor(remaining / 60);
        const s = remaining % 60;
        el.textContent = `${m}:${s.toString().padStart(2, "0")}`;
        if (remaining <= 0) {
          clearInterval(running.get(el));
          running.delete(el);
          el.classList.remove("is-running");
          el.classList.add("is-done");
          el.textContent = "✓ Done";
          beep();
          setTimeout(() => {
            el.textContent = original;
            el.classList.remove("is-done");
          }, 5000);
        }
      };
      tick();
      running.set(el, window.setInterval(tick, 1000));
    });
  });

  window.addEventListener("pagehide", () => {
    running.forEach((id) => clearInterval(id));
    running.clear();
  });
}

// --- Cook view (wake-lock + sticky toolbar + drawer-open + checkboxes) -------

function installCookMode(): void {
  const slug = RECIPE_SLUG;
  const btn = document.querySelector<HTMLButtonElement>('[data-action="cook-mode"]');
  if (!slug || !btn) return;
  // Hide the button entirely if Wake Lock isn't supported — most of cook mode
  // works without it but the headline benefit is the screen staying on.
  if (!("wakeLock" in navigator)) {
    btn.hidden = true;
    return;
  }

  const ingItems = Array.from(document.querySelectorAll<HTMLElement>(".ingredients-list li"));
  const stepItems = Array.from(document.querySelectorAll<HTMLElement>(".instructions-list li"));

  let wakeLock: WakeLockSentinel | null = null;
  let active = false;

  const checkboxKey = STORAGE_KEYS.cookMode(slug);
  const checked = new Set<string>(loadJson<string[]>(checkboxKey, []));
  const persist = () => sessionStorage.setItem(checkboxKey, JSON.stringify([...checked]));

  const addCheckboxes = (items: HTMLElement[], prefix: string) => {
    items.forEach((li, i) => {
      if (li.querySelector("input.tsm-check")) return;
      const id = `${prefix}-${i}`;
      // Wrap original content in a <label> so the checkbox has an accessible name.
      const wrapper = document.createElement("label");
      wrapper.className = "tsm-check-label";
      wrapper.style.display = "block";
      const cb = document.createElement("input");
      cb.type = "checkbox";
      cb.className = "tsm-check";
      cb.checked = checked.has(id);
      if (cb.checked) li.classList.add("is-done");
      cb.addEventListener("change", () => {
        if (cb.checked) { checked.add(id); li.classList.add("is-done"); }
        else { checked.delete(id); li.classList.remove("is-done"); }
        persist();
      });
      wrapper.appendChild(cb);
      while (li.firstChild) wrapper.appendChild(li.firstChild);
      li.appendChild(wrapper);
    });
  };

  const removeCheckboxes = (items: HTMLElement[]) => {
    items.forEach((li) => {
      const wrapper = li.querySelector<HTMLLabelElement>("label.tsm-check-label");
      if (!wrapper) return;
      // Move the original step content back out, then drop the wrapper + checkbox.
      while (wrapper.firstChild) {
        if ((wrapper.firstChild as HTMLElement).matches?.("input.tsm-check")) {
          wrapper.removeChild(wrapper.firstChild);
        } else {
          li.appendChild(wrapper.firstChild);
        }
      }
      wrapper.remove();
      li.classList.remove("is-done");
    });
  };

  const acquireLock = async () => {
    try { wakeLock = (await navigator.wakeLock?.request("screen")) ?? null; }
    catch { /* user-agent denied */ }
  };

  const toggle = () => {
    active = !active;
    document.body.classList.toggle("cook-mode", active);
    btn.classList.toggle("is-active", active);
    btn.setAttribute("aria-pressed", active ? "true" : "false");
    if (active) {
      addCheckboxes(ingItems, "ing");
      addCheckboxes(stepItems, "step");
      acquireLock();
    } else {
      removeCheckboxes(ingItems);
      removeCheckboxes(stepItems);
      wakeLock?.release(); wakeLock = null;
    }
  };

  btn.addEventListener("click", toggle);
  document.addEventListener("visibilitychange", () => {
    if (document.visibilityState === "visible" && active) acquireLock();
  });
}

// --- Favorites + made-it -----------------------------------------------------

function installFavorites(): void {
  const slug = RECIPE_SLUG;
  const heart = document.querySelector<HTMLButtonElement>('[data-action="favorite"]');
  const made = document.querySelector<HTMLButtonElement>('[data-action="made-it"]');
  if (!slug || !heart || !made) return;

  const updateHeart = () => {
    const favs = loadJson<FavoritesStore>(STORAGE_KEYS.favorites, { favorites: [] });
    const isFav = favs.favorites.includes(slug);
    heart.textContent = isFav ? "♥ Saved" : "♡ Save";
    heart.classList.toggle("is-active", isFav);
    heart.setAttribute("aria-pressed", isFav ? "true" : "false");
  };
  heart.addEventListener("click", () => {
    const favs = loadJson<FavoritesStore>(STORAGE_KEYS.favorites, { favorites: [] });
    favs.favorites = favs.favorites.includes(slug)
      ? favs.favorites.filter((s) => s !== slug)
      : [...favs.favorites, slug];
    saveJson(STORAGE_KEYS.favorites, favs);
    updateHeart();
  });
  updateHeart();

  made.addEventListener("click", () => {
    const note = prompt("Optional note (280 chars max):", "");
    if (note === null) return;
    const notes = loadJson<NotesStore>(STORAGE_KEYS.notes, {});
    if (!notes[slug]) notes[slug] = [];
    notes[slug].push({ date: new Date().toISOString(), note: note.slice(0, 280) });
    saveJson(STORAGE_KEYS.notes, notes);
    made.textContent = "Saved!";
    setTimeout(() => { made.textContent = "I made this"; }, 1500);
  });
}

// --- Shopping list -----------------------------------------------------------

function installShoppingList(): void {
  const slug = RECIPE_SLUG;
  const title = RECIPE_TITLE;
  const btn = document.querySelector<HTMLButtonElement>('[data-action="add-to-list"]');
  if (!slug || !title || !btn) return;
  const ingItems = Array.from(document.querySelectorAll<HTMLElement>(".ingredients-list li"));
  if (!ingItems.length) { btn.hidden = true; return; }

  btn.addEventListener("click", () => {
    const shop = loadJson<ShoppingStore>(STORAGE_KEYS.shoppingList, { items: [] });
    ingItems.forEach((li) => {
      shop.items.push({ recipeSlug: slug, recipeTitle: title, text: (li.textContent || "").trim(), checked: false });
    });
    saveJson(STORAGE_KEYS.shoppingList, shop);
    btn.textContent = `Added ${ingItems.length} items ✓`;
    setTimeout(() => { btn.textContent = "Add to list"; }, 1800);
  });
}

// --- Sticky mobile drawer ----------------------------------------------------

function installDrawer(): void {
  const ingredients = document.getElementById("recipe-ingredients");
  if (!ingredients) return;

  const drawer = document.createElement("button");
  drawer.type = "button";
  drawer.className = "tsm-drawer-toggle no-print";
  drawer.setAttribute("aria-label", "Show ingredients");
  drawer.setAttribute("aria-controls", "recipe-ingredients");
  drawer.setAttribute("aria-expanded", "false");
  drawer.textContent = "Ingredients ▲";
  const close = () => {
    document.body.classList.remove("drawer-open");
    drawer.setAttribute("aria-expanded", "false");
    drawer.textContent = "Ingredients ▲";
  };
  drawer.addEventListener("click", () => {
    const open = document.body.classList.toggle("drawer-open");
    drawer.setAttribute("aria-expanded", open ? "true" : "false");
    drawer.textContent = open ? "Hide ▼" : "Ingredients ▲";
  });
  // Resizing past the desktop breakpoint hides the toggle but the body class
  // (and aria state) would otherwise stick — reset on transition.
  matchMedia("(min-width: 1024px)").addEventListener("change", (e) => {
    if (e.matches) close();
  });
  document.body.appendChild(drawer);
}

// --- Print recipe card (4×6) -------------------------------------------------

function installPrintCard(): void {
  const btn = document.querySelector<HTMLButtonElement>('[data-action="print-card"]');
  if (!btn || !RECIPE_SLUG) return;
  btn.addEventListener("click", () => {
    // Inject a top-level @page rule because @page can't be selector-scoped via body.print-card.
    const styleEl = document.createElement("style");
    styleEl.id = "tsm-print-card-page";
    styleEl.textContent = "@page { size: 4in 6in; margin: 0.25in; }";
    document.head.appendChild(styleEl);
    document.body.classList.add("print-card");
    window.print();
    setTimeout(() => {
      document.body.classList.remove("print-card");
      styleEl.remove();
    }, 200);
  });
}

// --- Recently viewed (records the visit; rendered on homepage) ---------------

function recordRecent(): void {
  const slug = RECIPE_SLUG;
  const title = RECIPE_TITLE;
  if (!slug || !title) return;
  const store = loadJson<RecentStore>(STORAGE_KEYS.recent, { recent: [] });
  // Skip the write if this recipe is already at the front and was recorded
  // recently — avoids serializing the whole list on every refresh / back-nav.
  const head = store.recent[0];
  if (head?.slug === slug && Date.now() - new Date(head.visitedAt).getTime() < RECENT_DEDUPE_MS) {
    return;
  }
  store.recent = [
    { slug, title, visitedAt: new Date().toISOString() },
    ...store.recent.filter((r) => r.slug !== slug),
  ].slice(0, RECENT_LIMIT);
  saveJson(STORAGE_KEYS.recent, store);
}

// --- Boot --------------------------------------------------------------------

onReady(() => {
  installScaling();
  installUnits();
  installTimers();
  installCookMode();
  installFavorites();
  installShoppingList();
  installPrintCard();
  installDrawer();
  recordRecent();
});
