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
