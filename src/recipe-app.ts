// Recipe page client app: cook mode, timers, scaling, units, favorites,
// shopping list, sticky drawer. Each feature self-installs only if the
// relevant DOM markers are present.

import { STORAGE_KEYS, loadJson, onReady, saveJson } from "./util.js";

interface FavoritesStore { favorites: string[]; }
interface NotesStore { [slug: string]: { date?: string; note?: string }[]; }
interface ShoppingItem { recipeSlug: string; recipeTitle: string; text: string; checked: boolean; }
interface ShoppingStore { items: ShoppingItem[]; }

function recipeSlug(): string {
  return document.body.dataset.recipeSlug || "";
}

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

function ensureToolbar(): HTMLElement {
  let t = document.getElementById("tsm-toolbar");
  if (t) return t;
  t = document.createElement("div");
  t.id = "tsm-toolbar";
  t.className = "no-print";
  const header = document.querySelector("article > div > header");
  if (header && header.parentNode) {
    header.parentNode.insertBefore(t, header.nextSibling);
  } else {
    document.body.prepend(t);
  }
  return t;
}

function installScaling(): void {
  const ingItems = Array.from(document.querySelectorAll<HTMLElement>(".ingredients-list li"));
  if (!ingItems.length) return;

  const slug = recipeSlug();
  const saved = parseFloat(sessionStorage.getItem(STORAGE_KEYS.scale(slug)) || "1");
  let factor = saved || 1;
  let cached = false;

  const apply = () => {
    if (!cached) {
      // Cache originals lazily — most page loads never scale, so don't pay this cost upfront.
      ingItems.forEach((li) => { li.dataset.origHtml = li.innerHTML; });
      cached = true;
    }
    sessionStorage.setItem(STORAGE_KEYS.scale(slug), factor.toString());
    document.body.classList.toggle("is-scaled", factor !== 1);

    ingItems.forEach((li) => {
      const orig = li.dataset.origHtml || "";
      // Match every numeric token (mixed fraction, fraction, decimal, integer) inside
      // the (qty unit) parens — recipes like "5 cups, 22 1/2 oz" carry parallel
      // measurements and we need to scale all of them, not just the first.
      li.innerHTML = orig.replace(/\(([^)]+)\)/, (full, body) => {
        // Bare-number bodies (e.g. "(3)" eggs) round to a whole count.
        const bare = body.trim().match(/^\d+(?:\.\d+)?$/);
        if (bare) {
          return `(${Math.max(1, Math.round(parseFloat(bare[0]) * factor))})`;
        }
        const NUMBER_RE = /\d+\s+\d+\/\d+|\d+\/\d+|\d+(?:\.\d+)?/g;
        const scaled = body.replace(NUMBER_RE, (match: string) => {
          const amt = parseAmount(match);
          return amt === null ? match : smartFraction(amt * factor);
        });
        return `(${scaled})`;
      });
    });
  };

  const toolbar = ensureToolbar();
  const wrap = document.createElement("div");
  wrap.className = "tsm-tool";
  wrap.innerHTML = `
    <span class="tsm-tool-label">Scale</span>
    ${[0.5, 1, 2].map((f) => `<button data-factor="${f}" class="tsm-btn ${f === factor ? "is-active" : ""}">${f === 0.5 ? "½×" : f + "×"}</button>`).join("")}
  `;
  wrap.querySelectorAll<HTMLButtonElement>("button").forEach((btn) => {
    btn.addEventListener("click", () => {
      factor = parseFloat(btn.dataset.factor || "1");
      wrap.querySelectorAll("button").forEach((b) => b.classList.remove("is-active"));
      btn.classList.add("is-active");
      apply();
    });
  });
  toolbar.appendChild(wrap);
  if (factor !== 1) apply();
}

function installUnits(): void {
  // °F / °C in step text. Fresh regex per test() call so the `g` flag's lastIndex doesn't leak.
  const stepLis = Array.from(document.querySelectorAll<HTMLElement>(".instructions-list li"));
  const hasTemps = stepLis.some((li) => /(\d+(?:\.\d+)?)\s*°\s*([FC])/i.test(li.textContent || ""));
  if (!hasTemps) return;

  let metric = localStorage.getItem(STORAGE_KEYS.units) === "metric";
  const toolbar = ensureToolbar();
  const wrap = document.createElement("div");
  wrap.className = "tsm-tool";
  wrap.innerHTML = `
    <span class="tsm-tool-label">Units</span>
    <button class="tsm-btn ${metric ? "" : "is-active"}" data-units="us">US</button>
    <button class="tsm-btn ${metric ? "is-active" : ""}" data-units="metric">Metric</button>
  `;
  toolbar.appendChild(wrap);

  const apply = () => {
    document.body.classList.toggle("is-metric", metric);
    stepLis.forEach((li) => {
      if (li.dataset.origHtmlUnits === undefined) li.dataset.origHtmlUnits = li.innerHTML;
      li.innerHTML = li.dataset.origHtmlUnits.replace(/(\d+(?:\.\d+)?)\s*°\s*([FC])/gi, (full, n, unit) => {
        const num = parseFloat(n);
        if (metric && /F/i.test(unit)) return `${Math.round((num - 32) * 5 / 9)}°C`;
        if (!metric && /C/i.test(unit)) return `${Math.round(num * 9 / 5 + 32)}°F`;
        return full;
      });
    });
  };

  wrap.querySelectorAll<HTMLButtonElement>("button").forEach((btn) => {
    btn.addEventListener("click", () => {
      metric = btn.dataset.units === "metric";
      localStorage.setItem(STORAGE_KEYS.units, metric ? "metric" : "us");
      wrap.querySelectorAll("button").forEach((b) => b.classList.remove("is-active"));
      btn.classList.add("is-active");
      apply();
    });
  });
  if (metric) apply();
}

const TIMER_UNIT_SECONDS: Record<string, number> = {
  second: 1, seconds: 1, sec: 1, secs: 1, s: 1,
  minute: 60, minutes: 60, min: 60, mins: 60, m: 60,
  hour: 3600, hours: 3600, hr: 3600, hrs: 3600, h: 3600,
};

function installTimers(): void {
  const timers = Array.from(document.querySelectorAll<HTMLElement>(".timer[data-value]"));
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
      } catch {/* audio unavailable */}
    }
    navigator.vibrate?.([200, 100, 200]);
  };

  timers.forEach((el) => {
    const value = parseFloat(el.dataset.value || "0");
    const unit = (el.dataset.unit || "minutes").toLowerCase().split(/\s+/)[0];
    const seconds = Math.round(value * (TIMER_UNIT_SECONDS[unit] || 60));
    if (!seconds) return;

    el.classList.add("is-clickable");
    el.setAttribute("role", "button");
    el.setAttribute("tabindex", "0");
    el.title = "Click to start timer";

    const start = () => {
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
    };

    el.addEventListener("click", start);
    el.addEventListener("keydown", (e) => {
      if (e.key === "Enter" || e.key === " ") { e.preventDefault(); start(); }
    });
  });

  // Free timer intervals if the page goes away (e.g. bfcache restore).
  window.addEventListener("pagehide", () => {
    running.forEach((id) => clearInterval(id));
    running.clear();
  });
}

function installCookMode(): void {
  const slug = recipeSlug();
  if (!slug) return;
  const ingItems = Array.from(document.querySelectorAll<HTMLElement>(".ingredients-list li"));
  const stepItems = Array.from(document.querySelectorAll<HTMLElement>(".instructions-list li"));
  if (!ingItems.length && !stepItems.length) return;

  let wakeLock: WakeLockSentinel | null = null;
  let active = false;

  const checkboxKey = STORAGE_KEYS.cookMode(slug);
  const checked = new Set<string>(loadJson<string[]>(checkboxKey, []));
  const persist = () => sessionStorage.setItem(checkboxKey, JSON.stringify([...checked]));

  const addCheckboxes = (items: HTMLElement[], prefix: string) => {
    items.forEach((li, i) => {
      if (li.querySelector("input.tsm-check")) return;
      const id = `${prefix}-${i}`;
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
      li.prepend(cb);
    });
  };

  const acquireLock = async () => {
    try { wakeLock = (await navigator.wakeLock?.request("screen")) ?? null; }
    catch {/* lock denied */}
  };
  const releaseLock = () => { wakeLock?.release(); wakeLock = null; };

  const toggle = () => {
    active = !active;
    document.body.classList.toggle("cook-mode", active);
    if (active) {
      addCheckboxes(ingItems, "ing");
      addCheckboxes(stepItems, "step");
      acquireLock();
    } else {
      releaseLock();
    }
  };

  const toolbar = ensureToolbar();
  const btn = document.createElement("button");
  btn.className = "tsm-btn tsm-cook-btn";
  btn.textContent = "Cook mode";
  btn.addEventListener("click", () => {
    toggle();
    btn.classList.toggle("is-active", active);
  });
  toolbar.appendChild(btn);

  document.addEventListener("visibilitychange", () => {
    if (document.visibilityState === "visible" && active) acquireLock();
  });
}

function installFavorites(): void {
  const slug = recipeSlug();
  if (!slug) return;
  const toolbar = ensureToolbar();

  const heart = document.createElement("button");
  heart.className = "tsm-btn tsm-fav";
  const updateHeart = () => {
    const favs = loadJson<FavoritesStore>(STORAGE_KEYS.favorites, { favorites: [] });
    const isFav = favs.favorites.includes(slug);
    heart.textContent = isFav ? "♥ Saved" : "♡ Save";
    heart.classList.toggle("is-active", isFav);
  };
  heart.addEventListener("click", () => {
    const favs = loadJson<FavoritesStore>(STORAGE_KEYS.favorites, { favorites: [] });
    if (favs.favorites.includes(slug)) {
      favs.favorites = favs.favorites.filter((s) => s !== slug);
    } else {
      favs.favorites.push(slug);
    }
    saveJson(STORAGE_KEYS.favorites, favs);
    updateHeart();
  });
  updateHeart();
  toolbar.appendChild(heart);

  const made = document.createElement("button");
  made.className = "tsm-btn";
  made.textContent = "I made this";
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
  toolbar.appendChild(made);
}

function installShoppingList(): void {
  const slug = recipeSlug();
  const recipeTitle = document.querySelector(".recipe-title")?.textContent || "";
  if (!slug || !recipeTitle) return;
  const ingItems = Array.from(document.querySelectorAll<HTMLElement>(".ingredients-list li"));
  if (!ingItems.length) return;

  const toolbar = ensureToolbar();
  const btn = document.createElement("button");
  btn.className = "tsm-btn";
  btn.textContent = "Add to list";
  btn.addEventListener("click", () => {
    const shop = loadJson<ShoppingStore>(STORAGE_KEYS.shoppingList, { items: [] });
    ingItems.forEach((li) => {
      shop.items.push({ recipeSlug: slug, recipeTitle, text: (li.textContent || "").trim(), checked: false });
    });
    saveJson(STORAGE_KEYS.shoppingList, shop);
    btn.textContent = "Added ✓";
    setTimeout(() => { btn.textContent = "Add to list"; }, 1500);
  });
  toolbar.appendChild(btn);
}

function installDrawer(): void {
  if (!document.querySelector(".recipe-ingredients")) return;
  const drawer = document.createElement("button");
  drawer.className = "tsm-drawer-toggle no-print";
  drawer.setAttribute("aria-label", "Show ingredients");
  drawer.textContent = "Ingredients ▲";
  drawer.addEventListener("click", () => {
    document.body.classList.toggle("drawer-open");
    drawer.textContent = document.body.classList.contains("drawer-open") ? "Hide ▼" : "Ingredients ▲";
  });
  document.body.appendChild(drawer);
}

function installPrintCard(): void {
  if (!recipeSlug()) return;
  const toolbar = ensureToolbar();
  const btn = document.createElement("button");
  btn.className = "tsm-btn";
  btn.textContent = "Print card";
  btn.addEventListener("click", () => {
    document.body.classList.add("print-card");
    window.print();
    setTimeout(() => document.body.classList.remove("print-card"), 200);
  });
  toolbar.appendChild(btn);
}

onReady(() => {
  installScaling();
  installUnits();
  installTimers();
  installCookMode();
  installFavorites();
  installShoppingList();
  installPrintCard();
  installDrawer();
});
