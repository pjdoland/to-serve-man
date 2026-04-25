"""
Static site generator for To Serve Man cookbook.

Generates a complete static website from Cooklang recipes.
"""

import json
import logging
import secrets
import shutil
from pathlib import Path

import markdown
from jinja2 import Environment, FileSystemLoader
from slugify import slugify

import config
from recipe_parser import (
    Callout,
    Cookware,
    Ingredient,
    Recipe,
    RecipeCollection,
    Section,
    Step,
    Text,
    Timer,
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

        # Set up Jinja2 environment
        self.jinja_env = Environment(loader=FileSystemLoader(config.TEMPLATES_DIR), autoescape=True)

        # Markdown processor
        self.md = markdown.Markdown(extensions=["extra", "nl2br"])

        # Load recipes
        self.collection = RecipeCollection(self.recipes_dir)
        self.collection.load_recipes(use_cooklang_parser=False)

    def load_markdown_content(self, filename: str) -> str:
        """Load and convert markdown content to HTML."""
        filepath = self.content_dir / filename
        if filepath.exists():
            with open(filepath, encoding="utf-8") as f:
                return self.md.convert(f.read())
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

    def parse_recipe_content(self, recipe: Recipe) -> tuple[str, str]:
        """Render the recipe body to (ingredients_html, instructions_html)."""
        parsed = recipe.parsed_body()

        # Ingredients list — only @x{...} appear (matches legacy: bare @x stays inline-only).
        ing_items: list[str] = []
        for ing in parsed.ingredients:
            if not ing.from_braces:
                continue
            qty = ing.qty_display
            ing_items.append(f"<li>{ing.name} ({qty})</li>" if qty else f"<li>{ing.name}</li>")
        ingredients_html = "<ul>\n" + "\n".join(ing_items) + "\n</ul>"

        # Instructions — sections become <h3>, steps go into the surrounding <ol>.
        parts: list[str] = []
        current_steps: list[str] = []

        def flush_steps():
            if current_steps:
                parts.append("<ol>")
                parts.extend(f"<li>{s}</li>" for s in current_steps)
                parts.append("</ol>")
                current_steps.clear()

        for block in parsed.blocks:
            if isinstance(block, Section):
                flush_steps()
                parts.append(f'<h3 class="section-header">{block.name}</h3>')
            elif isinstance(block, Callout):
                flush_steps()
                label = block.kind.capitalize()
                parts.append(
                    f'<aside class="callout callout-{block.kind}" role="note">'
                    f'<strong class="callout-label">{label}</strong> '
                    f"<span>{block.text}</span></aside>"
                )
            else:
                current_steps.append(self._render_step_html(block))
        flush_steps()

        return ingredients_html, "\n".join(parts)

    @staticmethod
    def _render_step_html(step: Step) -> str:
        out: list[str] = []
        for tok in step.tokens:
            if isinstance(tok, Text):
                out.append(tok.text)
            elif isinstance(tok, Ingredient):
                out.append(f'<span class="ingredient">{tok.name}</span>')
            elif isinstance(tok, Cookware):
                out.append(f'<span class="cookware">{tok.name}</span>')
            elif isinstance(tok, Timer):
                out.append(f'<span class="timer">{tok.display}</span>')
        return "".join(out)

    def _resolve_cross_refs(self, recipe: Recipe) -> dict[str, list[Recipe]]:
        """Resolve serve_with/pairs_with/uses slugs to Recipe objects; warn on misses."""
        by_slug = {r.slug: r for r in self.collection.recipes}
        resolved: dict[str, list[Recipe]] = {}
        for field_name in ("serve_with", "pairs_with", "uses"):
            slugs = getattr(recipe, field_name)
            hits: list[Recipe] = []
            for s in slugs:
                target = by_slug.get(s)
                if target:
                    hits.append(target)
                else:
                    logger.warning(f"{recipe.filepath}: unknown {field_name} slug '{s}'")
            if hits:
                resolved[field_name] = hits
        return resolved

    def generate_recipe_page(self, recipe: Recipe):
        """Generate individual recipe page."""
        ingredients_html, instructions_html = self.parse_recipe_content(recipe)
        cross_refs = self._resolve_cross_refs(recipe)
        context = {
            "recipe": recipe,
            "ingredients_html": ingredients_html,
            "instructions_html": instructions_html,
            "cross_refs": cross_refs or None,
        }
        output_path = self.output_dir / "recipes" / recipe.slug / "index.html"
        self.render_template("recipe.html", context, output_path)

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
        }

        output_path = self.output_dir / "index.html"
        self.render_template("index.html", context, output_path)

    def generate_list_page(self, title: str, recipes: list[Recipe], output_path: Path, subtitle: str = None):
        """Generate a list page (category, tag, etc.)."""
        context = {
            "title": title,
            "subtitle": subtitle,
            "recipes": recipes,
        }

        self.render_template("list.html", context, output_path)

    def generate_category_pages(self):
        """Generate pages for each category."""
        categories = self.collection.get_by_category()

        for category, recipes in categories.items():
            title = category.replace("-", " ").title()
            output_path = self.output_dir / category / "index.html"
            self.generate_list_page(title, recipes, output_path)

    def generate_tag_pages(self):
        """Generate pages for each tag."""
        tags = self.collection.get_by_tag()

        for tag, recipes in tags.items():
            slug = slugify(tag)
            output_path = self.output_dir / "tags" / slug / "index.html"
            self.generate_list_page(f"#{tag}", recipes, output_path)

    def generate_cuisine_pages(self):
        """Generate pages for each cuisine."""
        cuisines = self.collection.get_by_cuisine()

        for cuisine, recipes in cuisines.items():
            slug = slugify(cuisine)
            output_path = self.output_dir / "cuisine" / slug / "index.html"
            self.generate_list_page(cuisine, recipes, output_path, subtitle="Food recipes")

    def generate_spirit_pages(self):
        """Generate pages for each spirit."""
        spirits = self.collection.get_by_spirit()

        for spirit, recipes in spirits.items():
            slug = slugify(spirit)
            output_path = self.output_dir / "spirit" / slug / "index.html"
            self.generate_list_page(f"{spirit.title()} Cocktails", recipes, output_path)

    def generate_facet_pages(self, attr: str, segment: str, label: str):
        """Generate /<segment>/<value>/ pages for a multi-value Recipe facet (e.g. season, occasion)."""
        groups: dict[str, list[Recipe]] = {}
        for recipe in self.collection.recipes:
            for value in getattr(recipe, attr) or []:
                groups.setdefault(value, []).append(recipe)
        for value, recipes in groups.items():
            slug = slugify(value)
            output_path = self.output_dir / segment / slug / "index.html"
            self.generate_list_page(value.title(), recipes, output_path, subtitle=f"{label}: {value}")

    def generate_about_page(self):
        """Generate about page."""
        about_content = self.load_markdown_content("about.md")

        context = {
            "about_content": about_content,
        }
        output_path = self.output_dir / "about" / "index.html"
        self.render_template("about.html", context, output_path)

    def generate_food_page(self):
        """Generate main food page."""
        recipes = self.collection.food_recipes
        output_path = self.output_dir / "food" / "index.html"
        self.generate_list_page("Food", recipes, output_path, subtitle="All food recipes")

    def generate_cocktails_page(self):
        """Generate main cocktails page."""
        recipes = self.collection.cocktail_recipes
        output_path = self.output_dir / "cocktails" / "index.html"
        self.generate_list_page("Cocktails", recipes, output_path, subtitle="All cocktail recipes")

    def generate_search_data(self):
        """Generate JSON search data for client-side search."""
        search_data = {"recipes": []}

        for recipe in self.collection.recipes:
            recipe_data = {
                "title": recipe.title,
                "slug": recipe.slug,
                "description": recipe.description or "",
                "tags": recipe.tags,
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

        # Generate about page
        logger.info("  Generating about page...")
        self.generate_about_page()

        # Generate food and cocktails pages
        logger.info("  Generating food and cocktails pages...")
        self.generate_food_page()
        self.generate_cocktails_page()

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
