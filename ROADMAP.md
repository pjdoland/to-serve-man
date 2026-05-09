# Roadmap

Consensus report from a multi-persona codebase review (2026-05-07).

## Process recap

1. **Independent review** by 7 personas (backend, frontend, a11y/UX, SEO/perf, PM/cookbook author, devops, content systems) — each produced 30 items (10 enhancements + 10 features + 10 bugs).
2. **Deduplication** of 210 raw items into a master list of **138 unique suggestions**.
3. **Peer voting** — every persona cast a Y/N on every item with rationale on Ns.
4. **Borda tabulation** (each Y = 1 point; max = 7).
5. **Filter** to 6/7 or 7/7 consensus.

---

## Consensus distribution (138 items)

| Score | Count | What this means |
|------:|------:|--|
| 7/7 | 3 | Universal agreement |
| 6/7 | 17 | Strong consensus, one domain dissent |
| 5/7 | 27 | Meaningful but not universal |
| 4/7 | 32 | Half house, half not |
| 3/7 | 22 | Niche / single-domain wins |
| ≤2/7 | 37 | Rejected |

The **20 finalists** (6/7+) are listed below. Persona codes: **B**ackend, **F**rontend, **A**11y, **S**EO/perf, **P**M, **D**evOps, **C**ontent.

---

## Borda ranking table — finalists (6/7+)

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

**Pattern:** the dissents cluster — DevOps reflexively votes N on content cleanup (out of his domain), SEO/perf votes N on build correctness (no Core Web Vitals impact), A11y votes N on schema/SEO (no SR users care). The 6/7 items are real consensus, just blocked from 7/7 by domain narrowness.

---

## Recommended work, grouped by effort

### 1. Easiest to implement (11 items — half-day each or less)

#### Fix JSON-LD escaping in `templates/recipe.html`
The recipe schema interpolates `recipe.title`, `recipe.description`, and `recipe.metadata.author` directly into the JSON-LD body using Jinja's HTML autoescape — but JSON-LD requires JSON-escaping (e.g. `&quot;` is not valid in a JSON string). The Mai Tai's `hero_alt` already contains `"Suck 'Em Up"`; an author with a backslash would silently kill rich-result eligibility on every recipe page.
- **Difficulty:** Easy (S) — render the JSON dict in `site_generator.py` via `json.dumps()`, pass as a single `safe` blob to the template.
- **Impact:** Fixes a broken-by-design SEO feature on 158 pages; unlocks Recipe rich results.
- **Risk:** None.

#### Generate `sitemap.xml`
No sitemap is emitted, so search engines have to discover all 161 recipe pages plus tag/cuisine/spirit/season facet pages by crawling alone. Add a `sitemap.xml` writer in `site_generator.py` using `.cook` mtimes for `<lastmod>`.
- **Difficulty:** Easy (S).
- **Impact:** Faster initial indexing; large win for a 200-page site that just doubled in size.
- **Risk:** None. Pair with `robots.txt` for the `Sitemap:` pointer (item 13 missed 6/7 by a hair).

#### Resolve the Macadamia Nut Chi Chi duplicate
Two `.cook` files describe the same drink: `099-macadamia-nut-chi-chi.cook` (rank 99, hurricane glass, full Phase-3 schema, 4 oz pineapple) and orphan `macadamia-nut-chi-chi.cook` (no rank, tiki mug, 8 oz pineapple, malformed `2 1/2%oz` quantity). Both slugify to the same URL — one will silently overwrite the other depending on filesystem traversal order.
- **Difficulty:** Easy (S) — pick one, delete the other, possibly merge useful content.
- **Impact:** Removes a real correctness bug; future-proofs URL-uniqueness assumption.
- **Risk:** Lose the variant interpretation if not consciously merged.

#### Renumber the 4 orphan cocktails
`negroni.cook`, `margarita.cook`, `paper-plane.cook`, and `macadamia-nut-chi-chi.cook` lack a `rank:` field and use a different schema (have `difficulty`, no `year`/`source_author`/footnotes). They sort inconsistently on listings and break the 1–150 numbered convention everyone else follows.
- **Difficulty:** Easy (S) — `git mv` + frontmatter edits.
- **Impact:** Restores cataloging consistency; eliminates one-off code paths in any future `rank`-based feature.
- **Risk:** Slug changes break inbound links — add 301 redirects via `_redirects` (or accept the breakage on a personal site).

#### Glassware facet fragmentation cleanup (`collins`/`old-fashioned`/`hurricane`)
Facet aggregation produces three "old-fashioned"-style buckets (`old-fashioned`, `old fashioned`), two "collins" (`collins`, `collins glass`), two "hurricane" (`hurricane`, `hurricane glass`), and four moai mug variants. Each becomes a separate `/cocktails/glass/<slug>/` page with a fraction of the inventory.
- **Difficulty:** Easy (S) — search/replace across `recipes/cocktails/*.cook`.
- **Impact:** Consolidates thin facet pages; fewer dead-end clicks for the user.
- **Risk:** Best done after item 81 (controlled vocabulary) lands so the canonical list is decided.

#### Ingredient capitalization splits cleanup
`Gosling's Black Seal rum` and `Gosling's Black Seal Rum` co-exist as distinct ingredients across the corpus. Cooklang dedupes lowercased keys *within* a file but not *across* files, so any future ingredient index treats them as separate items.
- **Difficulty:** Easy (S).
- **Impact:** Foundational for the ingredient ontology (item 86).
- **Risk:** None.

#### `lime juice` vs `fresh lime juice` canonicalization
95 occurrences of `fresh lime juice` and 8 of `lime juice` mean the same liquid, two ingredient buckets. Same shape: `orange juice` (9) vs `fresh orange juice` (29), `pineapple juice` (18) vs `fresh pineapple juice` (13) vs `unsweetened pineapple juice` (12).
- **Difficulty:** Easy (S) — search/replace, with judgement on the canonical form ("fresh ___ juice" preferred for citrus).
- **Impact:** Future ingredient index, search facet, and shopping list aggregation all become correct.
- **Risk:** Loses some authorial nuance ("unsweetened pineapple juice" carries information).

#### Populate or remove `recipes/basics/` + `season`/`occasion` fields
The schema documents `season` and `occasion` and the site generator builds `/season/<value>/` and `/occasion/<value>/` pages, but **zero** `.cook` files set them — every facet route is empty. Same for the `basics` category folder.
- **Difficulty:** Easy (S) for removal; Moderate if backfilling content.
- **Impact:** Removes dead code paths and empty pages, OR turns an unused affordance into a real browsing dimension.
- **Risk:** Removal + future re-add is more code churn than backfilling — decide which way.

#### Add HTML link-checker to CI (lychee or htmltest)
Recipes cross-reference each other via `serve_with`/`pairs_with`/`uses` slugs, and `BASE_URL` rewriting is brittle. A `lychee docs/` step after build catches broken internal links and stale external sources before they hit `main`.
- **Difficulty:** Easy (S) — one CI step.
- **Impact:** Hardens deploy gate; prevents broken-link rot.
- **Risk:** External URL flakiness can cause spurious failures — use `--skip-missing` or scope to internal links initially.

#### `compile_pdf` swallows stale-PDF failures
The success check is `if returncode != 0 and not (output_dir / "cookbook.pdf").exists()`. A stale `cookbook.pdf` from a previous successful build causes the function to return `True` even when `pdflatex` fails — silent stale output ships to production.
- **Difficulty:** Easy (S) — `os.unlink` the PDF before compile, or check returncode unconditionally.
- **Impact:** Closes a silent-failure mode that would let LaTeX regressions ship.
- **Risk:** None.

#### `PDFGenerator.generate_all` swallows compile failure
`generate_all` calls `compile_pdf()` and logs on failure — but `build_pdf()` in `build.py` returns `True` regardless because `generate_all` doesn't propagate the boolean. CI currently sees a failed PDF compile as success.
- **Difficulty:** Easy (S) — bubble the boolean up.
- **Impact:** Same as #126 — closes a silent failure mode.
- **Risk:** None. Best landed alongside #126.

---

### 2. Moderate effort (7 items — half-day to a few days each)

#### Build-time link checker (parser-side, not CI-side)
`_resolve_cross_refs` already warns on bad slugs but doesn't fail the build, and `metadata.source` URLs are never validated. Add a `--strict` mode to `build.py` that turns warnings into errors plus an opt-in HTTP HEAD check for external sources, with on-disk caching so it doesn't run every build.
- **Difficulty:** Moderate (M) — internal slug validation is fast; HTTP checking needs a cache layer.
- **Impact:** Author catches broken cross-refs locally before push; complements CI link-checker.
- **Risk:** External HEAD checks can race against rate-limited servers — keep them opt-in.

#### Centralize controlled vocabularies in `config.py`
`glass`, `spirit_base`, `cuisine`, and `tags` are freeform strings parsed straight from frontmatter and bucketed via `sorted({r.glass for r in ...})`. Promote them to `GLASSWARE`, `SPIRITS`, `CUISINES`, `TAG_VOCABULARY` enums (with alias maps) so facet pages and validators have a single source of truth.
- **Difficulty:** Moderate (M).
- **Impact:** Foundation for items 82 (canonicalization), 90 (glassware cleanup), 86 (ingredient ontology), and the JSON Schema.
- **Risk:** Decisions about canonical forms can stall — timebox the vocab decision and ship.

#### Canonicalize facet keys before bucketing
`RecipeCollection.get_by_spirit` / `get_by_cuisine` / `get_by_tag` and `generate_facet_pages` group by raw value, producing the fragmentation in items 90/91/92. Add a `_canonical(value, vocab)` helper that lowercases, strips, and applies the vocab alias map before bucketing — and call it at every aggregation point.
- **Difficulty:** Moderate (M) — touches several aggregation sites.
- **Impact:** Permanently prevents the class of bug in 90/91/92 from recurring as content grows.
- **Risk:** Depends on item 81 landing first.

#### Validate at parse time + propagate failures
Today `Recipe.from_path` parses then defers validation to `validate()`, and `RecipeCollection.load_recipes` swallows per-file errors via `try/except Exception: logger.exception(...)` with no return signal. A YAML syntax error on one file produces a build that's missing one recipe with no CI signal. Restructure as `Recipe.load(path) -> Result[Recipe, list[Error]]` and propagate failures through `build.py` so CI exits non-zero.
- **Difficulty:** Moderate (M).
- **Impact:** Eliminates an entire class of silent build defects.
- **Risk:** May surface real existing errors that have been silently shipping — fix those first or run with a warn-only flag for one deploy.

#### Estimated reading time + step count
Add "12 steps · ~6 min read · 30 min active cooking" near the H1. Helps readers with chronic fatigue or time pressure scope a recipe before diving in. Also good for SR users to understand size before traversing all steps.
- **Difficulty:** Moderate (M) — straightforward computation, but defining "active cooking" needs judgment.
- **Impact:** UX wins on every recipe page; small SEO benefit (rich snippet eligibility).
- **Risk:** Step counting depends on parser segmentation — verify the count matches what users see.

#### Backfill `variations` + cross-refs (`serve_with`/`pairs_with`/`uses`) across recipes
The schema supports these and the template renders them — but no recipe uses them. A Negroni page with linked variations (Boulevardier, Sbagliato, White Negroni) would feel like a real cookbook chapter; carbonara → cacio e pepe → amatriciana is the same play.
- **Difficulty:** Moderate (M) for tooling; content effort scales with editorial ambition.
- **Impact:** Massive — turns a flat catalog into a navigable cookbook; strong internal linking for SEO.
- **Risk:** Pure content work — easy to start, hard to "finish." Set a target subset (e.g., classic cocktails first).

#### Surface ingredients in search index
Search currently scores titles, tags, descriptions, cuisine/spirit — but not ingredients. Yet ingredients are how cooks actually search ("what can I make with leftover guanciale?"). Add ingredient names to `search-data.json` and the scoring function so a query for "campari" finds Negroni, Boulevardier, and Jungle Bird.
- **Difficulty:** Moderate (M) — extend `generate_search_data` and `search.ts` scoring.
- **Impact:** Transforms search from title-matching to actual content-matching; enables ingredient-substitution discovery.
- **Risk:** Bigger search index = more bytes; pair with item 19 (minify `search-data.json`, which scored 4/7) to keep payload reasonable.

---

### 3. Most difficult / architectural (2 items)

#### Allergen / dietary filter facet
Today the only way to know if a recipe is gluten-free, dairy-free, nut-free, shellfish-free, or alcohol-free is to read the full ingredient list. Surface filter chips on listing pages and indicators on recipe pages. Critical for users with celiac, severe allergies, or in recovery — and a strong content-discovery feature for everyone else.
- **Difficulty:** Hard (L) — requires (a) an ingredient-to-allergen map, (b) per-recipe derivation, (c) listing-page facet UI, (d) authorial overrides for borderline cases.
- **Impact:** Real accessibility/inclusion win; major discovery feature.
- **Risk:** Allergen claims have legal/health implications. Frame as "appears to contain X" with a disclaimer; require manual confirmation for severe allergens. Depends on item 86 (ingredient ontology).

#### Ingredient alias / `canonical_id` / `category` taxonomy
Build an ingredient ontology layer: each canonical ingredient gets an ID, an alias list (for parser canonicalization), and a category (`spirit/modifier/juice/syrup/bitters/garnish/ice/other`). Powers items 48 (allergens), 92/91 (canonicalization at the source), 106 (search), and the future build-a-bar / shopping-list-grouping features.
- **Difficulty:** Hard (L) — content modeling decision + parser integration + likely a new `ingredients/` directory of YAML files.
- **Impact:** Unlocks a generation of features (ontology-backed everything). Without it, items 48/86/92 keep being one-off patches.
- **Risk:** Schema design takes time; resist scope creep into "complete cocktail database." Start with the ~50 ingredients used in 5+ recipes.

---

## Suggested sequencing

1. **First commit, today:** items 88, 89, 126, 127 (correctness + content hygiene, no upstream dependencies).
2. **First week:** items 2, 12, 122 (SEO + CI hardening, all independent).
3. **First sprint:** items 81 → 82 → 90/91/92/93 (vocab → canonicalization → cleanup) — each unlocks the next.
4. **Behind the sprint:** items 72, 80 (build hardening), then 49, 106 (UX wins).
5. **Quarter-scale projects:** items 86 → 48 (ontology → allergen filter) and item 103 (variations backfill, mostly content).

20 items, 11 of them landable in a day each. The DevOps persona's domain bias means reasonable content/UX wins were under-represented in his ballot — the 6/7 set is genuinely the high-consensus list.
