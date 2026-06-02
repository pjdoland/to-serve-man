"""
Static site generator for To Serve Man cookbook.

Generates a complete static website from Cooklang recipes.
"""

import json
import logging
import secrets
import shutil
from datetime import date
from functools import cached_property
from pathlib import Path
from xml.sax.saxutils import escape as xml_escape

import markdown
from jinja2 import Environment, FileSystemLoader
from slugify import slugify

import config
from footnotes import Footnote, extract, tokenize_inline
from ingredient_ontology import canonical_ingredient
from recipe_parser import (
    RECIPE_NOTE_FIELDS,
    Callout,
    Cookware,
    Ingredient,
    Recipe,
    RecipeCollection,
    Section,
    Step,
    Text,
    Timer,
    canonical_facet,
    display_label,
)

logger = logging.getLogger("tsm.site")


class SiteGenerator:
    """Generates static website from recipes."""

    def __init__(self, recipes_dir: str = None, output_dir: str = None, base_url: str = None):
        self.recipes_dir = Path(recipes_dir or config.RECIPES_DIR)
        self.output_dir = Path(output_dir or config.DOCS_DIR)
        self.base_url = (base_url if base_url is not None else config.BASE_URL).rstrip("/")
        self.content_dir = Path(config.CONTENT_DIR)
        # New token each build so CDNs/browsers don't serve a stale copy after a recipe is added.
        self.cache_bust = secrets.token_hex(5)
        # Tracked across the build so callers can fail-fast under --strict
        # instead of having broken cross-refs silently warn-and-ship. List of
        # (recipe_filepath, field_name, missing_slug) tuples.
        self.cross_ref_failures: list[tuple[Path, str, str]] = []

        # Set up Jinja2 environment. Register canonical_facet + display_label
        # alongside slugify so templates can both bucket and humanize the same
        # way Python does (use canonical_facet, NOT bare slugify, for facet
        # URLs — bare slugify skips alias mapping).
        self.jinja_env = Environment(loader=FileSystemLoader(config.TEMPLATES_DIR), autoescape=True)
        self.jinja_env.filters["slugify"] = slugify
        self.jinja_env.filters["canonical_facet"] = canonical_facet
        self.jinja_env.filters["display_label"] = display_label

        # Markdown processor
        self.md = markdown.Markdown(extensions=["extra", "nl2br"])

        # Load recipes
        self.collection = RecipeCollection(self.recipes_dir)
        self.collection.load_recipes(use_cooklang_parser=False)

    def load_markdown_content(self, filename: str) -> str:
        """Load and convert markdown content to HTML."""
        try:
            return self.md.convert((self.content_dir / filename).read_text(encoding="utf-8"))
        except FileNotFoundError:
            return ""

    def clean_output_dir(self):
        """Remove and recreate output directory."""
        if self.output_dir.exists():
            shutil.rmtree(self.output_dir)
        self.output_dir.mkdir(parents=True, exist_ok=True)

    def copy_static_files(self):
        """Copy static assets to output directory."""
        static_src = Path("static")
        static_dest = self.output_dir / "static"

        if static_src.exists():
            shutil.copytree(static_src, static_dest, dirs_exist_ok=True)

        # Copy images if they exist
        images_src = Path("images")
        images_dest = self.output_dir / "images"

        if images_src.exists():
            shutil.copytree(images_src, images_dest, dirs_exist_ok=True)

    def render_template(self, template_name: str, context: dict, output_path: Path):
        """Render a Jinja2 template and write to file."""
        template = self.jinja_env.get_template(template_name)

        # Add site configuration to all contexts
        context["base_url"] = self.base_url
        context["site_title"] = config.COOKBOOK_TITLE
        context["site_description"] = config.COOKBOOK_DESCRIPTION
        context["site_author"] = config.COOKBOOK_AUTHOR
        context["site_url"] = config.SITE_URL
        context["cache_bust"] = self.cache_bust

        html = template.render(**context)

        # Ensure output directory exists
        output_path.parent.mkdir(parents=True, exist_ok=True)

        # Write file
        with open(output_path, "w", encoding="utf-8") as f:
            f.write(html)

    def parse_recipe_content(self, recipe: Recipe) -> tuple[str, str, str, str]:
        """Render the recipe body to (ingredients_html, headnotes_html, instructions_html, footnotes_html).

        Leading bare-`>` callouts split off as headnotes so the "Instructions"
        heading sits directly above the numbered steps. `[^N]: ...` paragraphs
        in any callout are pulled into a separate Sources section.
        """
        parsed = recipe.parsed

        ing_items: list[str] = []
        for ing in parsed.ingredients:
            if not ing.from_braces:
                continue
            qty = ing.qty_display
            ing_items.append(f"<li>{ing.name} ({qty})</li>" if qty else f"<li>{ing.name}</li>")
        ingredients_html = "<ul>\n" + "\n".join(ing_items) + "\n</ul>"

        headnote_blocks: list[Callout] = []
        body_blocks: list[Section | Step | Callout] = []
        seen_non_callout = False
        for block in parsed.blocks:
            if not seen_non_callout and isinstance(block, Callout):
                headnote_blocks.append(block)
            else:
                seen_non_callout = True
                body_blocks.append(block)

        all_callouts = headnote_blocks + [b for b in body_blocks if isinstance(b, Callout)]
        result = extract(all_callouts)
        cleaned_lookup = {id(orig): c for orig, c in zip(all_callouts, result.cleaned, strict=True)}
        defined_nums = {fn.num for fn in result.footnotes}

        headnotes_html = "\n".join(
            self._render_callout_html(cleaned_lookup[id(b)], defined_nums)
            for b in headnote_blocks
            if cleaned_lookup[id(b)] is not None
        )

        parts: list[str] = []
        current_steps: list[str] = []

        def flush_steps():
            if current_steps:
                parts.append("<ol>")
                parts.extend(f"<li>{s}</li>" for s in current_steps)
                parts.append("</ol>")
                current_steps.clear()

        for block in body_blocks:
            if isinstance(block, Section):
                flush_steps()
                parts.append(f'<h3 class="section-header">{block.name}</h3>')
            elif isinstance(block, Callout):
                cleaned = cleaned_lookup[id(block)]
                if cleaned is None:
                    continue
                flush_steps()
                parts.append(self._render_callout_html(cleaned, defined_nums))
            else:
                current_steps.append(self._render_step_html(block))
        flush_steps()

        footnotes_html = self._render_footnotes_html(result.footnotes, result.referenced, defined_nums)
        return ingredients_html, headnotes_html, "\n".join(parts), footnotes_html

    @staticmethod
    def _format_inline(text: str, defined_nums: set[int]) -> str:
        """Expand `[^N]` and `*italic*` markers in callout/footnote prose.

        Plain `text` segments are inserted verbatim so authors can drop in raw
        HTML (long-standing callout convention)."""
        out: list[str] = []
        tokens = list(tokenize_inline(text))
        for i, (kind, payload) in enumerate(tokens):
            if kind == "text":
                out.append(payload)
            elif kind == "ref":
                # Adjacent refs (e.g. [^2][^3]) render as a run of superscripts
                # that visually merges into one number. Insert a superscript
                # comma so "2,3" reads as two distinct citations.
                if i > 0 and tokens[i - 1][0] == "ref":
                    out.append('<sup class="footnote-ref-sep">,</sup>')
                if payload in defined_nums:
                    out.append(
                        f'<sup class="footnote-ref" id="fnref-{payload}">'
                        f'<a href="#fn-{payload}">{payload}</a></sup>'
                    )
                else:
                    out.append(f'<sup class="footnote-ref">{payload}</sup>')
            else:
                out.append(f"<em>{payload}</em>")
        return "".join(out)

    def _render_callout_html(self, block: Callout, defined_nums: set[int]) -> str:
        label_html = (
            f'<strong class="callout-label">{block.kind.capitalize()}</strong> ' if block.labeled else ""
        )
        body_html = "".join(
            f"<p>{self._format_inline(p, defined_nums)}</p>" for p in block.text.split("\n\n")
        )
        return f'<aside class="callout callout-{block.kind}" role="note">{label_html}{body_html}</aside>'

    def _render_footnotes_html(
        self, footnotes: list[Footnote], referenced: set[int], defined_nums: set[int]
    ) -> str:
        if not footnotes:
            return ""
        items: list[str] = []
        for fn in footnotes:
            body = self._format_inline(fn.text, defined_nums)
            backref = (
                f' <a href="#fnref-{fn.num}" class="footnote-backref" aria-label="Back to text">↩</a>'
                if fn.num in referenced
                else ""
            )
            items.append(f'<li id="fn-{fn.num}">{body}{backref}</li>')
        return (
            '<section class="recipe-footnotes" aria-label="Sources">'
            '<h2 class="font-serif text-2xl mb-6">Sources</h2>'
            f"<ol>{''.join(items)}</ol>"
            "</section>"
        )

    @staticmethod
    def _render_step_html(step: Step) -> str:
        out: list[str] = []
        for tok in step.tokens:
            if isinstance(tok, Text):
                out.append(tok.text)
            elif isinstance(tok, Ingredient):
                attrs = f' data-amount="{tok.qty}" data-unit="{tok.unit}"' if (tok.qty or tok.unit) else ""
                out.append(f'<span class="ingredient"{attrs}>{tok.name}</span>')
            elif isinstance(tok, Cookware):
                out.append(f'<span class="cookware">{tok.name}</span>')
            elif isinstance(tok, Timer):
                # Native <button> so AT announces it as a control + meets WCAG 2.5.8 target size.
                out.append(
                    f'<button type="button" class="timer" data-value="{tok.value}" data-unit="{tok.unit}" '
                    f'aria-label="Start {tok.display} timer">{tok.display}</button>'
                )
        return "".join(out)

    @cached_property
    def _by_slug(self) -> dict[str, Recipe]:
        return {r.slug: r for r in self.collection.recipes}

    def _resolve_cross_refs(self, recipe: Recipe) -> dict[str, list[Recipe]]:
        """Resolve serve_with/pairs_with/uses slugs to Recipe objects; warn on
        misses and record them on self.cross_ref_failures so build.py --strict
        can fail the build."""
        resolved: dict[str, list[Recipe]] = {}
        for field_name in ("serve_with", "pairs_with", "uses"):
            slugs = getattr(recipe, field_name)
            hits: list[Recipe] = []
            for s in slugs:
                target = self._by_slug.get(s)
                if target:
                    hits.append(target)
                else:
                    logger.warning(f"{recipe.filepath}: unknown {field_name} slug '{s}'")
                    self.cross_ref_failures.append((recipe.filepath, field_name, s))
            if hits:
                resolved[field_name] = hits
        return resolved

    def _recipe_breadcrumbs(self, recipe: Recipe) -> list[tuple[str, str | None]]:
        """Build the breadcrumb trail for a recipe page; last item has no href."""
        if recipe.is_cocktail:
            return [("Cocktails", f"{self.base_url}/cocktails/"), (recipe.title, None)]
        return [
            ("Food", f"{self.base_url}/food/"),
            (recipe.category.replace("-", " ").title(), f"{self.base_url}/food/{recipe.category}/"),
            (recipe.title, None),
        ]

    def generate_recipe_page(self, recipe: Recipe):
        """Generate individual recipe page."""
        ingredients_html, headnotes_html, instructions_html, footnotes_html = self.parse_recipe_content(
            recipe
        )
        cross_refs = self._resolve_cross_refs(recipe)
        notes = [
            (label, getattr(recipe, field)) for field, label in RECIPE_NOTE_FIELDS if getattr(recipe, field)
        ]
        context = {
            "recipe": recipe,
            "breadcrumbs": self._recipe_breadcrumbs(recipe),
            "ingredients_html": ingredients_html,
            "headnotes_html": headnotes_html,
            "instructions_html": instructions_html,
            "footnotes_html": footnotes_html,
            "cross_refs": cross_refs or None,
            "notes": notes,
            "nav_active": "cocktails" if recipe.is_cocktail else "food",
            "recipe_jsonld": self._recipe_jsonld(recipe),
        }
        output_path = self.output_dir / "recipes" / recipe.slug / "index.html"
        self.render_template("recipe.html", context, output_path)

    @cached_property
    def _site_origin(self) -> str | None:
        """Fully-qualified site origin (e.g. https://example.com/sub) for use
        in places that require an absolute URL (sitemap <loc>, JSON-LD image,
        OpenGraph). Returns None if SITE_URL isn't set to an http(s) URL —
        callers warn-and-skip rather than emit a broken artifact."""
        site_url = (config.SITE_URL or "").rstrip("/")
        if site_url.startswith(("http://", "https://")):
            return site_url
        return None

    def _recipe_jsonld(self, recipe: Recipe) -> str:
        """Build the Schema.org Recipe JSON-LD blob.

        Built in Python and json.dumps'd so quotes/newlines/backslashes in
        title/description/author can't produce invalid JSON. Field shape mirrors
        what the template emitted before — extending it (recipeIngredient,
        recipeInstructions, etc.) is a separate roadmap item.
        """
        data: dict = {
            "@context": "https://schema.org/",
            "@type": "Recipe",
            "name": recipe.title,
        }
        if recipe.description:
            data["description"] = recipe.description
        if recipe.metadata.get("author"):
            data["author"] = {"@type": "Person", "name": recipe.metadata["author"]}
        if recipe.prep_time:
            data["prepTime"] = recipe.prep_time
        if recipe.cook_time:
            data["cookTime"] = recipe.cook_time
        if recipe.servings:
            data["recipeYield"] = f"{recipe.servings} servings"
        if recipe.hero_image:
            # Schema.org requires an absolute URL for image; fall back to base_url
            # for local dev where SITE_URL is unset.
            origin = self._site_origin or self.base_url
            data["image"] = f"{origin}/{recipe.hero_image}"
        data["recipeCategory"] = recipe.category.title()
        return json.dumps(data, ensure_ascii=False)

    def generate_homepage(self):
        """Generate homepage."""
        hero_content = self.load_markdown_content("hero.md")

        context = {
            "recipes": self.collection.recipes,
            "categories": self.collection.get_by_category(),
            "tags": self.collection.get_by_tag(),
            "cuisines": self.collection.get_by_cuisine(),
            "spirits": self.collection.get_by_spirit(),
            "hero_content": hero_content,
            "is_homepage": True,
            "nav_active": "home",
        }

        output_path = self.output_dir / "index.html"
        self.render_template("index.html", context, output_path)

    def generate_list_page(
        self,
        title: str,
        recipes: list[Recipe],
        output_path: Path,
        subtitle: str = None,
        facets: list[dict] | None = None,
        breadcrumbs: list[tuple[str, str | None]] | None = None,
        nav_active: str | None = None,
    ):
        """Render a recipe-grid page (category, tag, cuisine, season, food landing, etc.).

        `facets` enables the client-side filter rail; `breadcrumbs` shows the trail.
        `nav_active` is the slug of the primary-nav item to mark with aria-current.
        """
        context = {
            "title": title,
            "subtitle": subtitle,
            "recipes": recipes,
            "facets": facets,
            "breadcrumbs": breadcrumbs,
            "nav_active": nav_active,
        }
        self.render_template("listing.html", context, output_path)

    def generate_category_pages(self):
        """Generate /food/<category>/ pages. Cocktails live under /cocktails/ (a single
        category), so only food categories get their own pages here."""
        categories = self.collection.get_by_category()

        for category, recipes in categories.items():
            if category == config.COCKTAIL_FOLDER:
                continue
            title = category.replace("-", " ").title()
            output_path = self.output_dir / "food" / category / "index.html"
            crumbs = [("Food", f"{self.base_url}/food/"), (title, None)]
            self.generate_list_page(title, recipes, output_path, breadcrumbs=crumbs, nav_active="food")

    def generate_tag_pages(self):
        """Generate pages for each tag. Keys from get_by_tag are already
        canonical (lowercased, slugified, alias-mapped) so they double as URL
        slugs. Tag display stays lowercase (hashtag convention)."""
        tags = self.collection.get_by_tag()

        for slug, recipes in tags.items():
            display = display_label(slug, titlecase=False)
            output_path = self.output_dir / "tags" / slug / "index.html"
            crumbs = [("Home", f"{self.base_url}/"), (f"#{display}", None)]
            self.generate_list_page(f"#{display}", recipes, output_path, breadcrumbs=crumbs)

    def generate_cuisine_pages(self):
        """Generate pages for each cuisine."""
        cuisines = self.collection.get_by_cuisine()

        for slug, recipes in cuisines.items():
            display = display_label(slug)
            output_path = self.output_dir / "cuisine" / slug / "index.html"
            crumbs = [("Food", f"{self.base_url}/food/"), (display, None)]
            self.generate_list_page(
                display, recipes, output_path, subtitle="Food recipes", breadcrumbs=crumbs, nav_active="food"
            )

    def generate_spirit_pages(self):
        """Generate pages for each spirit."""
        spirits = self.collection.get_by_spirit()

        for slug, recipes in spirits.items():
            display = display_label(slug)
            output_path = self.output_dir / "spirit" / slug / "index.html"
            crumbs = [("Cocktails", f"{self.base_url}/cocktails/"), (display, None)]
            self.generate_list_page(
                f"{display} Cocktails",
                recipes,
                output_path,
                breadcrumbs=crumbs,
                nav_active="cocktails",
            )

    def generate_facet_pages(self, attr: str, segment: str, label: str):
        """Generate /<segment>/<value>/ pages for a multi-value Recipe facet (e.g. season, occasion)."""
        groups: dict[str, list[Recipe]] = {}
        for recipe in self.collection.recipes:
            for value in getattr(recipe, attr) or []:
                key = canonical_facet(value, attr)
                if key:
                    groups.setdefault(key, []).append(recipe)
        for key, recipes in groups.items():
            display = display_label(key)
            output_path = self.output_dir / segment / key / "index.html"
            self.generate_list_page(display, recipes, output_path, subtitle=f"{label}: {display}")

    def generate_favorites_page(self):
        """Generate /favorites/ shell — content populated client-side from localStorage."""
        recipe_index = [
            {"slug": r.slug, "title": r.title, "url": f"{self.base_url}/recipes/{r.slug}/"}
            for r in self.collection.recipes
        ]
        context = {"recipe_index": recipe_index, "nav_active": "favorites"}
        output_path = self.output_dir / "favorites" / "index.html"
        self.render_template("favorites.html", context, output_path)

    def generate_shopping_list_page(self):
        """Generate /shopping-list/ shell — content populated client-side from localStorage."""
        output_path = self.output_dir / "shopping-list" / "index.html"
        self.render_template("shopping-list.html", {"nav_active": "shopping-list"}, output_path)

    def generate_about_page(self):
        """Generate about page."""
        about_content = self.load_markdown_content("about.md")

        context = {
            "about_content": about_content,
            "nav_active": "about",
        }
        output_path = self.output_dir / "about" / "index.html"
        self.render_template("about.html", context, output_path)

    @staticmethod
    def _facet(name: str, key: str, options: list[str]) -> dict:
        """Build a facet definition rendered as a multi-select dropdown."""
        return {"name": name, "key": key, "options": options}

    def generate_food_page(self):
        """Generate main food page with facet rail (cuisine + category)."""
        recipes = self.collection.food_recipes
        cuisines = sorted({r.cuisine for r in recipes if r.cuisine})
        categories = config.order_food_categories(sorted({r.category for r in recipes}))
        output_path = self.output_dir / "food" / "index.html"
        context = {
            "title": "Food",
            "subtitle": f"{len(recipes)} food recipes",
            "recipes": recipes,
            "facets": [
                self._facet("Cuisine", "cuisine", cuisines),
                self._facet("Category", "category", categories),
            ],
            "nav_active": "food",
        }
        self.render_template("listing.html", context, output_path)

    def generate_cocktails_page(self):
        """Generate main cocktails page with facet rail (spirit + glass)."""
        recipes = self.collection.cocktail_recipes
        spirits = sorted({r.spirit_base for r in recipes if r.spirit_base})
        glasses = sorted({r.glass for r in recipes if r.glass})
        output_path = self.output_dir / "cocktails" / "index.html"
        context = {
            "title": "Cocktails",
            "subtitle": f"{len(recipes)} cocktail recipes",
            "recipes": recipes,
            "facets": [
                self._facet("Spirit", "spirit_base", spirits),
                self._facet("Glass", "glass", glasses),
            ],
            "nav_active": "cocktails",
        }
        self.render_template("listing.html", context, output_path)

    def generate_search_data(self):
        """Generate JSON search data for client-side search.

        Includes ingredient names so a query for "campari" finds Negroni and
        Boulevardier even when "campari" isn't in title/description/tags. Only
        braced ingredients (the canonical list rendered as the ingredients
        UI) — bare mentions in step prose would inflate the index without
        clear benefit.

        Computes ontology coverage as a side effect for the build report.
        Canonical ids aren't serialized into the JSON yet — no client-side
        consumer reads them, and shipping ~30K of unused payload was flagged
        in PR review. Add the field back atomically with the first consumer
        (allergen filter / build-a-bar).
        """
        search_data = {"recipes": []}

        # Coverage counters surfaced in the build report so missing-from-
        # ontology ingredients don't silently grow the long tail.
        ontology_hits = ontology_misses = 0
        unmatched_examples: set[str] = set()

        for recipe in self.collection.recipes:
            raw_names = sorted({i.name for i in recipe.parsed.ingredients if i.from_braces})
            for name in raw_names:
                if canonical_ingredient(name):
                    ontology_hits += 1
                else:
                    ontology_misses += 1
                    unmatched_examples.add(name)
            recipe_data = {
                "title": recipe.title,
                "slug": recipe.slug,
                "description": recipe.description or "",
                "tags": recipe.tags,
                "ingredients": raw_names,
                "category": recipe.category,
                "is_cocktail": recipe.is_cocktail,
                "url": f"{self.base_url}/recipes/{recipe.slug}/",
            }

            if recipe.is_cocktail:
                recipe_data["spirit_base"] = recipe.spirit_base or ""
            else:
                recipe_data["cuisine"] = recipe.cuisine or ""

            search_data["recipes"].append(recipe_data)

        output_path = self.output_dir / "search-data.json"
        with open(output_path, "w", encoding="utf-8") as f:
            json.dump(search_data, f, ensure_ascii=False, indent=2)

        total = ontology_hits + ontology_misses
        if total:
            pct = ontology_hits / total * 100
            logger.info(
                f"  ✓ Ingredient ontology: {ontology_hits}/{total} mentions canonicalized "
                f"({pct:.1f}%, {len(unmatched_examples)} unique unmatched)"
            )

    def generate_sitemap(self):
        """Emit sitemap.xml covering recipes, listings, facets, and static pages.

        Per-recipe and per-facet lastmod uses .cook file mtime so unchanged
        sections of the sitemap stay byte-stable across builds. Static-page
        lastmod is omitted (Google treats absent identically to today, and we
        avoid daily churn in the diff).

        URL paths must mirror what generate_* methods write to disk: cuisines
        live under /cuisine/<slug>/ (NOT /food/), spirits under /spirit/<slug>/
        (NOT /cocktails/spirit/). Sitemap drift = 404 entries.
        """
        if not self._site_origin:
            logger.warning("  ⚠ SITE_URL not set to absolute http(s) URL; skipping sitemap.xml")
            return

        urls: list[tuple[str, str | None]] = []  # (path, lastmod or None)

        for path in ("/", "/food/", "/cocktails/", "/about/"):
            urls.append((path, None))

        recipe_mtimes: dict[str, str] = {}
        for recipe in self.collection.recipes:
            mtime = date.fromtimestamp(recipe.filepath.stat().st_mtime).isoformat()
            recipe_mtimes[recipe.slug] = mtime
            urls.append((f"/recipes/{recipe.slug}/", mtime))

        def _latest(recipes) -> str | None:
            mtimes = [recipe_mtimes[r.slug] for r in recipes if r.slug in recipe_mtimes]
            return max(mtimes) if mtimes else None

        for category, recipes in self.collection.get_by_category().items():
            food_recipes = [r for r in recipes if not r.is_cocktail]
            if food_recipes:
                urls.append((f"/food/{category}/", _latest(food_recipes)))

        # Keys from get_by_* are already canonical (lowercased + slugified +
        # alias-mapped) so they double as URL slugs — no second slugify needed.
        for tag, recipes in self.collection.get_by_tag().items():
            urls.append((f"/tags/{tag}/", _latest(recipes)))
        for cuisine, recipes in self.collection.get_by_cuisine().items():
            urls.append((f"/cuisine/{cuisine}/", _latest(recipes)))
        for spirit, recipes in self.collection.get_by_spirit().items():
            urls.append((f"/spirit/{spirit}/", _latest(recipes)))

        # Build XML by hand to avoid an extra dependency.
        lines = [
            '<?xml version="1.0" encoding="UTF-8"?>',
            '<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">',
        ]
        for path, lastmod in sorted(set(urls)):
            loc = xml_escape(self._site_origin + path)
            mod = f"<lastmod>{lastmod}</lastmod>" if lastmod else ""
            lines.append(f"  <url><loc>{loc}</loc>{mod}</url>")
        lines.append("</urlset>")

        (self.output_dir / "sitemap.xml").write_text("\n".join(lines) + "\n", encoding="utf-8")

    def generate_robots_txt(self):
        """Emit robots.txt; the Sitemap pointer is omitted when SITE_URL isn't
        an absolute http(s) URL (matches generate_sitemap's skip behavior)."""
        lines = ["User-agent: *", "Allow: /", "Disallow: /favorites/", "Disallow: /shopping-list/", ""]
        if self._site_origin:
            lines.append(f"Sitemap: {self._site_origin}/sitemap.xml")
        else:
            logger.warning("  ⚠ SITE_URL not absolute; robots.txt will lack Sitemap line")
        (self.output_dir / "robots.txt").write_text("\n".join(lines) + "\n", encoding="utf-8")

    def generate_all(self):
        """Generate complete static site."""
        logger.info("Generating site...")

        # Clean and prepare output directory
        logger.info("  Cleaning output directory...")
        self.clean_output_dir()

        # Copy static files
        logger.info("  Copying static files...")
        self.copy_static_files()

        # Generate homepage
        logger.info("  Generating homepage...")
        self.generate_homepage()

        # Generate search data
        logger.info("  Generating search data...")
        self.generate_search_data()

        # Generate recipe pages
        logger.info(f"  Generating {len(self.collection.recipes)} recipe pages...")
        for recipe in self.collection.recipes:
            self.generate_recipe_page(recipe)

        # Generate category pages
        logger.info("  Generating category pages...")
        self.generate_category_pages()

        # Generate tag pages
        logger.info("  Generating tag pages...")
        self.generate_tag_pages()

        # Generate cuisine pages
        logger.info("  Generating cuisine pages...")
        self.generate_cuisine_pages()

        # Generate spirit pages
        logger.info("  Generating spirit pages...")
        self.generate_spirit_pages()

        # Generate season/occasion pages
        logger.info("  Generating season/occasion pages...")
        self.generate_facet_pages("season", "season", "Season")
        self.generate_facet_pages("occasion", "occasion", "Occasion")

        # Generate favorites + shopping list shells
        logger.info("  Generating favorites + shopping-list shells...")
        self.generate_favorites_page()
        self.generate_shopping_list_page()

        # Generate about page
        logger.info("  Generating about page...")
        self.generate_about_page()

        # Generate food and cocktails pages
        logger.info("  Generating food and cocktails pages...")
        self.generate_food_page()
        self.generate_cocktails_page()

        # Generate sitemap.xml + robots.txt
        logger.info("  Generating sitemap.xml + robots.txt...")
        self.generate_sitemap()
        self.generate_robots_txt()

        logger.info(f"✓ Site generated successfully in {self.output_dir}/")


def generate_site(recipes_dir: str = None, output_dir: str = None, base_url: str = None):
    """
    Convenience function to generate site.

    Args:
        recipes_dir: Path to recipes directory (default: from config)
        output_dir: Path to output directory (default: from config)
        base_url: Base URL for the site (default: from config)
    """
    generator = SiteGenerator(recipes_dir, output_dir, base_url)
    generator.generate_all()


if __name__ == "__main__":
    generate_site()
