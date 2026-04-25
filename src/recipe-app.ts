export {}; // mark as module — keeps types isolated from sibling files

// Recipe page client app: cook mode, timers, scaling, units, favorites,
// shopping list, sticky drawer. Each feature self-installs only if the
// relevant DOM markers are present.

interface ScalingState {
  factor: number;
}

const STORAGE_KEYS = {
  scale: (slug: string) => `tsm:scale:${slug}`,
  units: "tsm:units",
  cookMode: (slug: string) => `tsm:cook:${slug}`,
  favorites: "tsm:favorites",
  notes: "tsm:notes",
  shoppingList: "tsm:shopping",
};

// --------- Helpers ---------

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
  // "1/2", "3/4"
  if (/^\d+\/\d+$/.test(trimmed)) {
    const [n, d] = trimmed.split("/").map(Number);
    return d ? n / d : null;
  }
  // "1 1/2"
  const mixed = trimmed.match(/^(\d+)\s+(\d+)\/(\d+)$/);
  if (mixed) {
    const [, w, n, d] = mixed;
    return parseInt(w) + parseInt(n) / parseInt(d);
  }
  const f = parseFloat(trimmed);
  return Number.isNaN(f) ? null : f;
}

// --------- Scaling ---------

function installScaling(): void {
  const ingredients = Array.from(document.querySelectorAll<HTMLElement>(".ingredient[data-amount]"));
  const ingItems = Array.from(document.querySelectorAll<HTMLElement>(".ingredients-list li"));
  if (!ingredients.length && !ingItems.length) return;

  // Cache originals so we can re-render at any factor.
  ingredients.forEach((el) => {
    el.dataset.origText = el.textContent || "";
  });
  ingItems.forEach((li) => {
    li.dataset.origHtml = li.innerHTML;
  });

  const slug = recipeSlug();
  const saved = parseFloat(sessionStorage.getItem(STORAGE_KEYS.scale(slug)) || "1");
  const state: ScalingState = { factor: saved || 1 };

  const apply = () => {
    const factor = state.factor;
    sessionStorage.setItem(STORAGE_KEYS.scale(slug), factor.toString());
    document.body.classList.toggle("is-scaled", factor !== 1);

    ingItems.forEach((li) => {
      const orig = li.dataset.origHtml || "";
      li.innerHTML = orig.replace(/\(([^)]+)\)/, (full, body) => {
        const m = body.match(/^([^\s]+)(?:\s+(.+))?$/);
        if (!m) return full;
        const amount = parseAmount(m[1]);
        if (amount === null) return full;
        const scaled = amount * factor;
        const isCount = !m[2] && scaled < 20;
        const display = isCount ? Math.max(1, Math.round(scaled)).toString() : smartFraction(scaled);
        return `(${display}${m[2] ? " " + m[2] : ""})`;
      });
    });
    ingredients.forEach((el) => {
      const amt = parseAmount(el.dataset.amount || "");
      if (amt === null) return;
      el.textContent = el.dataset.origText || "";
    });
    document.dispatchEvent(new CustomEvent("tsm:scaled", { detail: { factor } }));
  };

  const toolbar = ensureToolbar();
  const wrap = document.createElement("div");
  wrap.className = "tsm-tool";
  wrap.innerHTML = `
    <span class="tsm-tool-label">Scale</span>
    ${[0.5, 1, 2].map((f) => `<button data-factor="${f}" class="tsm-btn ${f === state.factor ? "is-active" : ""}">${f === 0.5 ? "½×" : f + "×"}</button>`).join("")}
  `;
  wrap.querySelectorAll<HTMLButtonElement>("button").forEach((btn) => {
    btn.addEventListener("click", () => {
      state.factor = parseFloat(btn.dataset.factor || "1");
      wrap.querySelectorAll("button").forEach((b) => b.classList.remove("is-active"));
      btn.classList.add("is-active");
      apply();
    });
  });
  toolbar.appendChild(wrap);
  if (state.factor !== 1) apply();
}

// --------- Units (US ↔ metric, temperatures + weights only) ---------

const UNIT_CONVERSIONS: Record<string, [string, (n: number) => number]> = {
  oz: ["g", (n) => Math.round(n * 28.35)],
  lb: ["kg", (n) => +(n * 0.4536).toFixed(2)],
  g: ["oz", (n) => +(n / 28.35).toFixed(2)],
  kg: ["lb", (n) => +(n / 0.4536).toFixed(2)],
};

function installUnits(): void {
  const tempEls = Array.from(document.querySelectorAll<HTMLElement>(".ingredient[data-unit]"));
  if (!tempEls.length) return;
  // Toggle: only add the toggle if any convertible units exist.
  const hasConvertible = tempEls.some((el) => {
    const u = (el.dataset.unit || "").toLowerCase();
    return u in UNIT_CONVERSIONS;
  });
  // Look for °F / °C in step text (pattern in raw text: "375°F").
  const tempRegex = /(\d+(?:\.\d+)?)\s*°\s*([FC])/gi;
  const stepLis = Array.from(document.querySelectorAll<HTMLElement>(".instructions-list li"));
  const hasTemps = stepLis.some((li) => tempRegex.test(li.textContent || ""));
  if (!hasConvertible && !hasTemps) return;

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
    // Temperature conversions in step text — done via DOM walk on first apply only.
    stepLis.forEach((li) => {
      const orig = li.dataset.origText ?? li.innerHTML;
      if (!li.dataset.origText) li.dataset.origText = orig;
      li.innerHTML = (li.dataset.origText || orig).replace(tempRegex, (full, n, unit) => {
        const num = parseFloat(n);
        if (metric && /F/i.test(unit)) {
          return `${Math.round((num - 32) * 5 / 9)}°C`;
        }
        if (!metric && /C/i.test(unit)) {
          return `${Math.round(num * 9 / 5 + 32)}°F`;
        }
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

// --------- Timers (tap-to-start) ---------

const TIMER_UNIT_SECONDS: Record<string, number> = {
  second: 1, seconds: 1, sec: 1, secs: 1, s: 1,
  minute: 60, minutes: 60, min: 60, mins: 60, m: 60,
  hour: 3600, hours: 3600, hr: 3600, hrs: 3600, h: 3600,
};

function installTimers(): void {
  const timers = Array.from(document.querySelectorAll<HTMLElement>(".timer[data-value]"));
  if (!timers.length) return;

  const running = new Map<HTMLElement, { remaining: number; intervalId: number }>();

  const beep = () => {
    try {
      const ctx = new (window.AudioContext || (window as any).webkitAudioContext)();
      const osc = ctx.createOscillator();
      const gain = ctx.createGain();
      osc.connect(gain); gain.connect(ctx.destination);
      osc.frequency.value = 880; gain.gain.value = 0.2;
      osc.start();
      setTimeout(() => { osc.stop(); ctx.close(); }, 800);
    } catch (e) { /* ignore */ }
    if ("vibrate" in navigator) navigator.vibrate?.([200, 100, 200]);
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
          const r = running.get(el);
          if (r) clearInterval(r.intervalId);
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
      const intervalId = window.setInterval(tick, 1000);
      running.set(el, { remaining, intervalId });
    };

    el.addEventListener("click", start);
    el.addEventListener("keydown", (e) => {
      if (e.key === "Enter" || e.key === " ") { e.preventDefault(); start(); }
    });
  });
}

// --------- Cook mode (wakelock + checkboxes + larger text) ---------

function installCookMode(): void {
  const slug = recipeSlug();
  if (!slug) return;
  const ingItems = Array.from(document.querySelectorAll<HTMLElement>(".ingredients-list li"));
  const stepItems = Array.from(document.querySelectorAll<HTMLElement>(".instructions-list li"));
  if (!ingItems.length && !stepItems.length) return;

  let wakeLock: any = null;
  let active = false;

  const checkboxKey = STORAGE_KEYS.cookMode(slug);
  const checked: Set<string> = new Set(JSON.parse(sessionStorage.getItem(checkboxKey) || "[]"));

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
    try { wakeLock = await (navigator as any).wakeLock?.request("screen"); }
    catch (e) { /* ignore */ }
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

// --------- Favorites + made-it ---------

interface FavoritesStore { favorites: string[]; }
interface NotesStore { [slug: string]: { date?: string; note?: string }[]; }

function loadFavs(): FavoritesStore {
  return JSON.parse(localStorage.getItem(STORAGE_KEYS.favorites) || '{"favorites":[]}');
}
function saveFavs(s: FavoritesStore): void {
  localStorage.setItem(STORAGE_KEYS.favorites, JSON.stringify(s));
}
function loadNotes(): NotesStore {
  return JSON.parse(localStorage.getItem(STORAGE_KEYS.notes) || "{}");
}
function saveNotes(n: NotesStore): void {
  localStorage.setItem(STORAGE_KEYS.notes, JSON.stringify(n));
}

function installFavorites(): void {
  const slug = recipeSlug();
  if (!slug) return;
  const toolbar = ensureToolbar();

  let favs = loadFavs();
  const heart = document.createElement("button");
  heart.className = "tsm-btn tsm-fav";
  const updateHeart = () => {
    const isFav = favs.favorites.includes(slug);
    heart.textContent = isFav ? "♥ Saved" : "♡ Save";
    heart.classList.toggle("is-active", isFav);
  };
  heart.addEventListener("click", () => {
    favs = loadFavs();
    if (favs.favorites.includes(slug)) {
      favs.favorites = favs.favorites.filter((s) => s !== slug);
    } else {
      favs.favorites.push(slug);
    }
    saveFavs(favs);
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
    const notes = loadNotes();
    if (!notes[slug]) notes[slug] = [];
    notes[slug].push({ date: new Date().toISOString(), note: note.slice(0, 280) });
    saveNotes(notes);
    made.textContent = "Saved!";
    setTimeout(() => { made.textContent = "I made this"; }, 1500);
  });
  toolbar.appendChild(made);
}

// --------- Shopping list ---------

interface ShoppingItem { recipeSlug: string; recipeTitle: string; text: string; checked: boolean; }
interface ShoppingStore { items: ShoppingItem[]; }

function loadShop(): ShoppingStore {
  return JSON.parse(localStorage.getItem(STORAGE_KEYS.shoppingList) || '{"items":[]}');
}
function saveShop(s: ShoppingStore): void {
  localStorage.setItem(STORAGE_KEYS.shoppingList, JSON.stringify(s));
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
    const shop = loadShop();
    ingItems.forEach((li) => {
      shop.items.push({ recipeSlug: slug, recipeTitle, text: (li.textContent || "").trim(), checked: false });
    });
    saveShop(shop);
    btn.textContent = "Added ✓";
    setTimeout(() => { btn.textContent = "Add to list"; }, 1500);
  });
  toolbar.appendChild(btn);
}

// --------- Sticky mobile drawer ---------

function installDrawer(): void {
  const ing = document.querySelector(".recipe-ingredients");
  if (!ing) return;
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

// --------- Toolbar plumbing ---------

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

// --------- Print recipe card (4×6) ---------

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

// --------- Boot ---------

function init(): void {
  installScaling();
  installUnits();
  installTimers();
  installCookMode();
  installFavorites();
  installShoppingList();
  installPrintCard();
  installDrawer();
}

if (document.readyState === "loading") {
  document.addEventListener("DOMContentLoaded", init);
} else {
  init();
}
