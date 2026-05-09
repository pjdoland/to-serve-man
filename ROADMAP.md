# Roadmap

Consensus report from a multi-persona codebase review (2026-05-07).

## Status

**All 11 items from the original work plan shipped.** The remaining 9 items
in the 6/7 Borda set were either explicitly deferred (content cleanup, UX
features) or never picked up. Section "Deferred or not picked up" below
tracks them.

| # | Item | Status |
|---:|---|---|
| 80 | Build-time link checker / `--strict` mode | ✓ shipped (phase 3a) |
| 82 | Canonicalize facet keys before bucketing | ✓ shipped (phase 2) |
| 122 | HTML link-checker in CI (lychee) | ✓ shipped (phase 1) |
| 2 | Fix JSON-LD escaping | ✓ shipped (phase 1) |
| 12 | Generate sitemap.xml + robots.txt | ✓ shipped (phase 1) |
| 72 | Validate at parse time + propagate failures | ✓ shipped (phase 2) |
| 81 | Centralize controlled vocabularies | ✓ shipped (phase 2) |
| 86 | Ingredient ontology | ✓ shipped (phase 4) |
| 88 | Resolve Macadamia Nut Chi Chi duplicate | ✓ shipped (deletion) |
| 89 | Renumber 4 orphan cocktails | ✓ shipped (deletion) |
| 106 | Surface ingredients in search index | ✓ shipped (phase 3a) |
| 126 | `compile_pdf` swallows stale-PDF failures | ✓ shipped (phase 1) |
| 127 | `PDFGenerator.generate_all` swallows compile failure | ✓ shipped (phase 1) |

## Deferred or not picked up (still on the 6/7 list)

| # | Item | Notes |
|---:|---|---|
| 48 | Allergen / dietary filter facet | Hard (L). Depends on the ingredient ontology (#86 — now shipped) plus an allergen tag per ingredient. Logical next architectural piece. |
| 49 | Estimated reading time + step count | Moderate (M). Pure rendering work. Pruned during planning to keep batches focused. |
| 90 | Glassware facet fragmentation cleanup | Easy (S). Content cleanup across `recipes/cocktails/*.cook`. Aliases now exist in `config.py` so the URLs are correct without touching .cook files; the actual content cleanup is still open. |
| 91 | Ingredient capitalization splits cleanup | Easy (S). Same shape as #90 — ontology now masks the bug at aggregation time, but content drift is still there. |
| 92 | `lime juice` vs `fresh lime juice` canonicalization | Easy (S). Same shape — the ingredient ontology aliases handle it for search/grouping; content unchanged. |
| 93 | Populate or remove recipes/basics + season/occasion | Easy (S). Decide whether to backfill the dead category/facets or delete the routes. |
| 103 | Backfill `variations` + cross-refs in recipe content | Moderate–hard. Pure content effort across 158 recipes; biggest lift. |

## Process recap (historical)

1. **Independent review** by 7 personas (backend, frontend, a11y/UX, SEO/perf, PM/cookbook author, devops, content systems) — each produced 30 items (10 enhancements + 10 features + 10 bugs).
2. **Deduplication** of 210 raw items into a master list of **138 unique suggestions**.
3. **Peer voting** — every persona cast a Y/N on every item with rationale on Ns.
4. **Borda tabulation** (each Y = 1 point; max = 7).
5. **Filter** to 6/7 or 7/7 consensus.

### Consensus distribution (138 items)

| Score | Count | What this means |
|------:|------:|--|
| 7/7 | 3 | Universal agreement |
| 6/7 | 17 | Strong consensus, one domain dissent |
| 5/7 | 27 | Meaningful but not universal |
| 4/7 | 32 | Half house, half not |
| 3/7 | 22 | Niche / single-domain wins |
| ≤2/7 | 37 | Rejected |

### Original Borda ranking — 6/7+ finalists

Persona codes: **B**ackend, **F**rontend, **A**11y, **S**EO/perf, **P**M, **D**evOps, **C**ontent.

| # | Item | Score | Supported by | Rejected by (reason) |
|---:|---|:---:|:---|:---|
| 80 | Build-time link checker (cross-refs + sources) | 7/7 | B F A S P D C | — |
| 82 | Canonicalize facet keys before bucketing | 7/7 | B F A S P D C | — |
| 122 | HTML link-checker in CI (lychee/htmltest) | 7/7 | B F A S P D C | — |
| 2 | Fix JSON-LD escaping (quotes/newlines/diacritics) | 6/7 | B F S P D C | A — schema cleanup, no a11y impact |
| 12 | Generate sitemap.xml | 6/7 | B F S P D C | A — crawler concern |
| 48 | Allergen / dietary filter facet | 6/7 | B F A S P C | D — UX feature |
| 49 | Estimated reading time + step count | 6/7 | B F A S P C | D — UX polish |
| 72 | Validate at parse time + propagate failures | 6/7 | B F A P D C | S — parser hardening, no SEO impact |
| 81 | Centralize controlled vocabularies in config (enums) | 6/7 | B F A P D C | S — config hygiene |
| 86 | Ingredient alias / canonical_id / category | 6/7 | B F A S P C | D — content concern |
| 88 | Resolve Macadamia Nut Chi Chi duplicate | 6/7 | B F A S P C | D — content dedup |
| 89 | Renumber 4 orphan cocktails (negroni/margarita/etc.) | 6/7 | B F A S P C | D — content renumber |
| 90 | Glassware facet fragmentation cleanup | 6/7 | B F A S P C | D — content cleanup |
| 91 | Ingredient capitalization splits cleanup | 6/7 | B F A S P C | D — content cleanup |
| 92 | `lime juice` vs `fresh lime juice` canonicalization | 6/7 | B F A S P C | D — content cleanup |
| 93 | Populate or remove recipes/basics + season/occasion | 6/7 | B F A S P C | D — content cleanup |
| 103 | Backfill `variations` + cross-refs in recipe content | 6/7 | B F A S P C | D — content backfill |
| 106 | Surface ingredients in search index | 6/7 | B F A S P C | D — search/UX feature |
| 126 | `compile_pdf` swallows stale-PDF failures | 6/7 | B F A P D C | S — build bug, no SEO |
| 127 | `PDFGenerator.generate_all` swallows compile failure | 6/7 | B F A P D C | S — build bug, no SEO |

**Pattern:** the dissents cluster — DevOps reflexively votes N on content cleanup (out of his domain), SEO/perf votes N on build correctness (no Core Web Vitals impact), A11y votes N on schema/SEO (no SR users care). The 6/7 items were real consensus, just blocked from 7/7 by domain narrowness.
