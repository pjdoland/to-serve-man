"""
Configuration management for To Serve Man cookbook.

Loads settings from .env file and provides defaults.
"""

import os
from pathlib import Path

from dotenv import load_dotenv

# Repo root — the directory this file lives in. Use for resolving asset paths
# from frontmatter (e.g. `hero_image: images/recipes/foo.jpg`) so resolution
# doesn't depend on the current working directory or recipe nesting depth.
PROJECT_ROOT = Path(__file__).resolve().parent

# Load .env file
load_dotenv(dotenv_path=PROJECT_ROOT / ".env")


def get_config(key: str, default: str = "") -> str:
    """Get configuration value from environment or use default."""
    return os.getenv(key, default)


# Cookbook Information
COOKBOOK_TITLE = get_config("COOKBOOK_TITLE", "To Serve Man")
COOKBOOK_DESCRIPTION = get_config("COOKBOOK_DESCRIPTION", "A personal collection of recipes worth keeping")
COOKBOOK_AUTHOR = get_config("COOKBOOK_AUTHOR", "")

# Website Configuration
BASE_URL = get_config("BASE_URL", "")
SITE_URL = get_config("SITE_URL", "")

# PDF Configuration
PDF_AUTHOR = get_config("PDF_AUTHOR", COOKBOOK_AUTHOR)
PDF_TITLE = get_config("PDF_TITLE", COOKBOOK_TITLE)

# Directories
RECIPES_DIR = "recipes"
OUTPUT_DIR = "output"
DOCS_DIR = "docs"
CONTENT_DIR = "content"
TEMPLATES_DIR = "templates"
STATIC_DIR = "static"
LATEX_DIR = "latex"

# Taxonomy — single source of truth for category ordering and the food/cocktail split.
# Folder name under recipes/ that holds cocktail recipes (also drives is_cocktail inference).
COCKTAIL_FOLDER = "cocktails"

# Display order for food categories. Anything outside this list is appended alphabetically.
FOOD_CATEGORY_ORDER = ["breakfast", "basics", "mains", "sides", "desserts"]


def order_food_categories(categories: list[str]) -> list[str]:
    """Return categories in canonical display order; unknown ones appended alphabetically."""
    known = [c for c in FOOD_CATEGORY_ORDER if c in categories]
    extra = sorted(c for c in categories if c not in FOOD_CATEGORY_ORDER)
    return known + extra


# --- Controlled vocabularies for facet aggregation --------------------------
#
# Aliases map non-canonical input forms (case/punctuation/synonyms) to the
# canonical key that becomes the URL slug + display label. When canonical_facet
# can't find an alias, it falls back to slugify(value), which still normalizes
# case/punctuation but won't merge synonyms. Aliases live here, not in the
# recipe content, so a typo in one .cook file doesn't fragment a facet page.
#
# Lookup keys are lowercased (the helper lowercases input first), so write
# aliases in lowercase too.

GLASSWARE_ALIASES = {
    "old fashioned": "old-fashioned",
    "hurricane glass": "hurricane",
    "collins glass": "collins",
}

SPIRIT_ALIASES = {
    "cachaça": "cachaca",
}

# Cuisines and tags currently rely on slugify alone — case/punctuation
# normalization handles the variations seen in the corpus today. Add explicit
# aliases here when synonyms appear (e.g. "italian american" vs
# "italian-american").
FACET_ALIASES: dict[str, dict[str, str]] = {
    "glass": GLASSWARE_ALIASES,
    "spirit_base": SPIRIT_ALIASES,
    "cuisine": {},
    "tag": {},
    "season": {},
    "occasion": {},
}


# Defensive: every alias *value* must already be a canonical slug (i.e.
# slugify(v) == v). Otherwise canonical_facet(canonical_facet(v)) would not
# round-trip and the sitemap could disagree with the page generator. Caught
# at import time so a bad alias addition fails the build.
def _check_alias_canonicality() -> None:
    from slugify import slugify  # local: keep slugify out of config's API

    for kind, aliases in FACET_ALIASES.items():
        for raw, canonical in aliases.items():
            if slugify(canonical) != canonical:
                raise AssertionError(
                    f"FACET_ALIASES[{kind!r}][{raw!r}] = {canonical!r} is not a "
                    f"canonical slug; slugify({canonical!r}) = {slugify(canonical)!r}"
                )


_check_alias_canonicality()
