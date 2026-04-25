"""
Recipe parser and validator for To Serve Man cookbook system.

Handles discovery, parsing, and validation of Cooklang recipe files.
"""

import logging
import re
from dataclasses import dataclass, field
from functools import cached_property
from pathlib import Path
from typing import Any

import yaml
from slugify import slugify

import config

logger = logging.getLogger("tsm.parser")

FRONTMATTER_RE = re.compile(r"^---\s*\n(.*?)\n---\s*\n", re.DOTALL)

# (field, label) pairs rendered in the recipe-notes block on both web and PDF.
RECIPE_NOTE_FIELDS: tuple[tuple[str, str], ...] = (
    ("yield_notes", "Yield"),
    ("make_ahead", "Make ahead"),
    ("storage", "Keeps"),
    ("reheats", "Reheat"),
)


def _as_list(value: Any) -> list[str]:
    """Normalize a YAML field that may be a string or list into list[str]."""
    if not value:
        return []
    return value if isinstance(value, list) else [value]


_TIME_RE = re.compile(r"(\d+)\s*(h|hour|hours|m|min|mins|minute|minutes)\b", re.IGNORECASE)


def _parse_minutes(value: str | None) -> int | None:
    """Parse "20 minutes", "1 hour 30 minutes", "1h", "30 min" into total minutes.
    Returns None if the value is missing or has no recognisable time tokens."""
    if not value:
        return None
    total = 0
    found = False
    for match in _TIME_RE.finditer(value):
        n = int(match.group(1))
        unit = match.group(2).lower()
        total += n * (60 if unit.startswith("h") else 1)
        found = True
    return total if found else None


# --- Cooklang body parsing ---------------------------------------------------

INGREDIENT_RE = re.compile(r"@([^{@#~]+?)\{([^}]*)\}")
INGREDIENT_NO_BRACE_RE = re.compile(r"@([^@#~{}\s]+)")
COOKWARE_BRACE_RE = re.compile(r"#([^@#~{}]+?)\{([^}]*)\}")
COOKWARE_NO_BRACE_RE = re.compile(r"#(\w+)")
TIMER_RE = re.compile(r"~\{([^}]+)\}")
# Order matters: braced forms must be tried before bare-word forms.
TOKEN_RE = re.compile(
    r"(?P<ing_brace>@[^{@#~]+?\{[^}]*\})"
    r"|(?P<cw_brace>#[^@#~{}]+?\{[^}]*\})"
    r"|(?P<ing>@[^@#~{}\s]+)"
    r"|(?P<cw>#\w+)"
    r"|(?P<timer>~\{[^}]+\})"
)


@dataclass(frozen=True)
class Ingredient:
    """An ingredient reference inside a step (e.g. @butter{2%tbsp}).

    `from_braces` distinguishes `@x{...}` (which appears in the ingredients list)
    from bare `@x` (which only gets highlighted inline).
    """

    name: str
    qty: str = ""  # "2", "3/4", "" for unspecified
    unit: str = ""  # "tbsp", "cup", "" for unitless
    from_braces: bool = True

    @property
    def qty_display(self) -> str:
        """Human-readable quantity ("2 tbsp", "3/4 cup", "")."""
        if self.qty and self.unit:
            return f"{self.qty} {self.unit}"
        return self.qty or self.unit


@dataclass(frozen=True)
class Cookware:
    name: str


@dataclass(frozen=True)
class Timer:
    value: str  # "30"
    unit: str = ""  # "seconds", "minutes"; "" if not specified

    @property
    def display(self) -> str:
        return f"{self.value} {self.unit}".strip()


@dataclass(frozen=True)
class Text:
    text: str


StepToken = Text | Ingredient | Cookware | Timer


@dataclass
class Step:
    """One instruction line, broken into typed tokens."""

    tokens: list[StepToken] = field(default_factory=list)


@dataclass
class Section:
    """A `>> Section name` header."""

    name: str


@dataclass
class Callout:
    """A `>note ...`, `>tip ...`, or `>warning ...` line — promoted to a styled aside."""

    kind: str  # "note" | "tip" | "warning"
    text: str


CALLOUT_KINDS = ("note", "tip", "warning")
_CALLOUT_RE = re.compile(rf"^>({'|'.join(CALLOUT_KINDS)})\s+(.+)$", re.IGNORECASE)


@dataclass
class ParsedBody:
    """Parsed Cooklang recipe body."""

    ingredients: list[Ingredient]  # Deduplicated, in first-appearance order.
    blocks: list[Section | Step | Callout]


def _split_qty(raw: str) -> tuple[str, str]:
    """Split Cooklang `qty%unit` into (qty, unit). `%` is the separator."""
    if "%" not in raw:
        return raw.strip(), ""
    qty, unit = raw.split("%", 1)
    return qty.strip(), unit.strip()


def _strip_frontmatter(raw: str) -> str:
    match = FRONTMATTER_RE.match(raw)
    return raw[match.end() :] if match else raw


def parse_body(raw_content: str) -> ParsedBody:
    """Parse a Cooklang recipe body into structured tokens.

    The output is renderer-agnostic: site_generator turns it into HTML,
    pdf_generator into LaTeX. Comments (`-- ...`) are dropped; section
    headers (`>> name`) become `Section` blocks; everything else is a `Step`
    whose tokens preserve the literal text interleaved with typed references.
    """
    body = _strip_frontmatter(raw_content)
    blocks: list[Section | Step | Callout] = []
    seen_ingredients: dict[str, Ingredient] = {}  # key: lowercased name
    ingredients_order: list[Ingredient] = []

    for raw_line in body.strip().split("\n"):
        line = raw_line.strip()
        if not line or line.startswith("--"):
            continue
        if line.startswith(">>"):
            blocks.append(Section(name=line[2:].strip()))
            continue
        callout_match = _CALLOUT_RE.match(line)
        if callout_match:
            blocks.append(Callout(kind=callout_match.group(1).lower(), text=callout_match.group(2).strip()))
            continue

        tokens: list[StepToken] = []
        cursor = 0
        for match in TOKEN_RE.finditer(line):
            if match.start() > cursor:
                tokens.append(Text(text=line[cursor : match.start()]))
            kind = match.lastgroup
            chunk = match.group()
            if kind == "ing_brace":
                m = INGREDIENT_RE.fullmatch(chunk)
                name = m.group(1).strip()
                qty, unit = _split_qty(m.group(2))
                ing = Ingredient(name=name, qty=qty, unit=unit)
                tokens.append(ing)
                key = name.lower()
                if key not in seen_ingredients:
                    seen_ingredients[key] = ing
                    ingredients_order.append(ing)
            elif kind == "ing":
                m = INGREDIENT_NO_BRACE_RE.fullmatch(chunk)
                name = m.group(1).strip()
                ing = Ingredient(name=name, from_braces=False)
                tokens.append(ing)
                key = name.lower()
                if key not in seen_ingredients:
                    seen_ingredients[key] = ing
                    ingredients_order.append(ing)
            elif kind == "cw_brace":
                m = COOKWARE_BRACE_RE.fullmatch(chunk)
                tokens.append(Cookware(name=m.group(1).strip()))
            elif kind == "cw":
                m = COOKWARE_NO_BRACE_RE.fullmatch(chunk)
                tokens.append(Cookware(name=m.group(1).strip()))
            elif kind == "timer":
                m = TIMER_RE.fullmatch(chunk)
                value, unit = _split_qty(m.group(1))
                tokens.append(Timer(value=value, unit=unit))
            cursor = match.end()
        if cursor < len(line):
            tokens.append(Text(text=line[cursor:]))
        blocks.append(Step(tokens=tokens))

    return ParsedBody(ingredients=ingredients_order, blocks=blocks)


# --- Recipe & RecipeCollection ----------------------------------------------


@dataclass
class Recipe:
    """A parsed recipe with metadata and (lazily) a parsed body."""

    filepath: Path
    raw_content: str
    metadata: dict[str, Any]
    is_cocktail: bool
    category: str
    slug: str

    @classmethod
    def from_path(cls, path: Path) -> "Recipe":
        raw_content = path.read_text(encoding="utf-8")
        metadata = cls._extract_metadata(raw_content)
        is_cocktail = metadata.get("type") == "cocktail" or path.parent.name == config.COCKTAIL_FOLDER
        slug = slugify(metadata.get("title", path.stem))
        return cls(
            filepath=path,
            raw_content=raw_content,
            metadata=metadata,
            is_cocktail=is_cocktail,
            category=path.parent.name,
            slug=slug,
        )

    @staticmethod
    def _extract_metadata(raw_content: str) -> dict[str, Any]:
        match = FRONTMATTER_RE.match(raw_content)
        if not match:
            return {}
        try:
            return yaml.safe_load(match.group(1)) or {}
        except yaml.YAMLError as e:
            raise ValueError(f"Invalid YAML frontmatter: {e}") from e

    @property
    def title(self) -> str:
        return self.metadata.get("title", "Untitled Recipe")

    @property
    def description(self) -> str | None:
        return self.metadata.get("description")

    @property
    def tags(self) -> list[str]:
        return self.metadata.get("tags", [])

    @property
    def cuisine(self) -> str | None:
        return self.metadata.get("cuisine")

    @property
    def spirit_base(self) -> str | None:
        return self.metadata.get("spirit_base")

    @property
    def difficulty(self) -> str | None:
        return self.metadata.get("difficulty")

    @property
    def servings(self) -> int | None:
        servings = self.metadata.get("servings")
        if servings is None:
            return None
        try:
            return int(servings)
        except (ValueError, TypeError):
            return None

    @property
    def prep_time(self) -> str | None:
        return self.metadata.get("prep_time")

    @property
    def cook_time(self) -> str | None:
        return self.metadata.get("cook_time")

    @cached_property
    def total_time(self) -> str | None:
        """Sum of prep+cook in minutes if both parse cleanly; otherwise display "Xh Ym"
        when each piece is recognisable. Falls back to None for free-form ('overnight')."""
        prep = _parse_minutes(self.prep_time)
        cook = _parse_minutes(self.cook_time)
        if prep is None and cook is None:
            return None
        total = (prep or 0) + (cook or 0)
        if total == 0:
            return None
        h, m = divmod(total, 60)
        if h and m:
            return f"{h}h {m}m"
        return f"{h}h" if h else f"{m} min"

    @property
    def hero_image(self) -> str | None:
        """Path to hero photo, relative to site root (e.g. 'images/recipes/foo.jpg')."""
        return self.metadata.get("hero_image")

    @property
    def hero_alt(self) -> str | None:
        """Optional alt text for the hero image — required if hero_image is set."""
        return self.metadata.get("hero_alt")

    @property
    def glass(self) -> str | None:
        return self.metadata.get("glass")

    @property
    def garnish(self) -> str | None:
        return self.metadata.get("garnish")

    # --- Phase 3 schema additions (all optional) ----------------------------

    @property
    def headnote(self) -> str | None:
        """Cook's voice / story preamble (markdown)."""
        return self.metadata.get("headnote")

    @property
    def yield_notes(self) -> str | None:
        """Qualitative yield info ('freezes 3 months raw')."""
        return self.metadata.get("yield_notes")

    @property
    def make_ahead(self) -> str | None:
        return self.metadata.get("make_ahead")

    @property
    def storage(self) -> str | None:
        return self.metadata.get("storage")

    @property
    def reheats(self) -> str | None:
        return self.metadata.get("reheats")

    @property
    def variations(self) -> list[dict[str, str]]:
        """List of {name, swap, note} dicts."""
        return self.metadata.get("variations") or []

    @property
    def serve_with(self) -> list[str]:
        """Slugs of recipes to serve with this one."""
        return self.metadata.get("serve_with") or []

    @property
    def pairs_with(self) -> list[str]:
        return self.metadata.get("pairs_with") or []

    @property
    def uses(self) -> list[str]:
        """Slugs of recipes used as components in this one."""
        return self.metadata.get("uses") or []

    @property
    def season(self) -> list[str]:
        """One or more of: spring, summer, fall, winter, year-round."""
        return _as_list(self.metadata.get("season"))

    @property
    def occasion(self) -> list[str]:
        """One or more of: weeknight, dinner-party, holiday, brunch, hangover, etc."""
        return _as_list(self.metadata.get("occasion"))

    @cached_property
    def parsed(self) -> ParsedBody:
        """The parsed Cooklang body (sections, steps, callouts, ingredients)."""
        return parse_body(self.raw_content)

    def parsed_body(self) -> ParsedBody:
        """Backwards-compatible alias for `parsed`."""
        return self.parsed

    def validate(self) -> list[str]:
        errors = []
        if not self.title or self.title == "Untitled Recipe":
            errors.append(f"{self.filepath}: Missing required field 'title'")
        if self.is_cocktail:
            if not self.spirit_base:
                errors.append(f"{self.filepath}: Cocktail recipes should have 'spirit_base'")
            if not self.glass:
                errors.append(f"{self.filepath}: Cocktail recipes should have 'glass'")
        elif not self.cuisine:
            errors.append(f"{self.filepath}: Food recipes should have 'cuisine'")
        return errors


class RecipeCollection:
    """Manages a collection of recipes."""

    def __init__(self, recipes_dir: Path):
        self.recipes_dir = Path(recipes_dir)
        self.recipes: list[Recipe] = []
        self._loaded = False

    def discover_recipes(self) -> list[Path]:
        if not self.recipes_dir.exists():
            raise FileNotFoundError(f"Recipes directory not found: {self.recipes_dir}")
        return list(self.recipes_dir.rglob("*.cook"))

    def load_recipes(self, use_cooklang_parser: bool = False):
        """Load and parse all recipes. `use_cooklang_parser` is accepted for backward-compat and ignored."""
        del use_cooklang_parser
        for recipe_file in self.discover_recipes():
            try:
                self.recipes.append(Recipe.from_path(recipe_file))
            except Exception:
                logger.exception(f"Error loading recipe {recipe_file}")
        self._loaded = True
        return self.recipes

    def validate_all(self) -> dict[str, list[str]]:
        if not self._loaded:
            self.load_recipes()
        all_errors = {}
        for recipe in self.recipes:
            errors = recipe.validate()
            if errors:
                all_errors[str(recipe.filepath)] = errors
        return all_errors

    def get_by_category(self) -> dict[str, list[Recipe]]:
        out: dict[str, list[Recipe]] = {}
        for recipe in self.recipes:
            out.setdefault(recipe.category, []).append(recipe)
        return out

    def get_by_tag(self) -> dict[str, list[Recipe]]:
        out: dict[str, list[Recipe]] = {}
        for recipe in self.recipes:
            for tag in recipe.tags:
                out.setdefault(tag, []).append(recipe)
        return out

    def get_by_cuisine(self) -> dict[str, list[Recipe]]:
        out: dict[str, list[Recipe]] = {}
        for recipe in self.recipes:
            if not recipe.is_cocktail and recipe.cuisine:
                out.setdefault(recipe.cuisine, []).append(recipe)
        return out

    def get_by_spirit(self) -> dict[str, list[Recipe]]:
        out: dict[str, list[Recipe]] = {}
        for recipe in self.recipes:
            if recipe.is_cocktail and recipe.spirit_base:
                out.setdefault(recipe.spirit_base, []).append(recipe)
        return out

    @property
    def food_recipes(self) -> list[Recipe]:
        return [r for r in self.recipes if not r.is_cocktail]

    @property
    def cocktail_recipes(self) -> list[Recipe]:
        return [r for r in self.recipes if r.is_cocktail]


def load_and_parse_recipes(recipes_dir: str = "recipes") -> RecipeCollection:
    collection = RecipeCollection(Path(recipes_dir))
    collection.load_recipes()
    return collection
