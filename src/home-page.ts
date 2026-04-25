// Homepage client: populates the "Recently Viewed" rail from localStorage.

import { type RecentStore, STORAGE_KEYS, escapeHtml, loadJson, onReady } from "./util.js";

function init(): void {
  const section = document.getElementById("recently-viewed");
  const list = section?.querySelector<HTMLElement>("[data-recently-viewed-list]");
  if (!section || !list) return;

  const baseUrl = document.documentElement.dataset.baseUrl || "";
  const { recent } = loadJson<RecentStore>(STORAGE_KEYS.recent, { recent: [] });
  if (!recent.length) return;

  list.innerHTML = recent.map((r) => `
    <a href="${escapeHtml(baseUrl)}/recipes/${escapeHtml(r.slug)}/" class="recipe-card">
      <div class="card-eyebrow">Recently Viewed</div>
      <h3 class="card-title">${escapeHtml(r.title)}</h3>
    </a>
  `).join("");
  section.dataset.hasItems = "1";
}

onReady(init);
