"""Ingredient ontology loader and lookup.

Loads `ingredients.yaml` once, exposes `canonical_ingredient(name)` for
mapping a raw recipe ingredient string to its canonical id (or None when
the ingredient isn't yet modeled — long-tail items are intentionally
allowed to fall through). Also exposes `category_of(canonical_id)` for
faceting consumers.

Validation runs at load time: every alias must be unique across the whole
file, every category must be a known value, every id must be a clean
slug. Bad data fails the import with a clear message instead of silently
mis-bucketing recipes downstream.
"""

import logging
from dataclasses import dataclass
from functools import cache

import yaml
from slugify import slugify

import config

logger = logging.getLogger("tsm.ontology")

CATEGORIES = frozenset(
    {"spirit", "modifier", "juice", "syrup", "bitters", "garnish", "ice", "dairy", "other"}
)


@dataclass(frozen=True)
class Ontology:
    """Loaded ontology — a flat alias→id map and an id→category map."""

    alias_to_id: dict[str, str]
    id_to_category: dict[str, str]

    @property
    def ids(self) -> list[str]:
        return sorted(self.id_to_category)


def _normalize(value: str) -> str:
    """Match the lookup-key shape used by canonical_ingredient — lowercased
    and whitespace-trimmed. Aliases are normalized once at load time so the
    runtime lookup is a single dict get."""
    return value.lower().strip()


@cache
def _load() -> Ontology:
    """Read and validate ingredients.yaml. Cached for the process lifetime —
    edits to the file require a restart, same as Python source."""
    path = config.INGREDIENTS_FILE
    if not path.exists():
        # Soft-fail: returning an empty ontology means the rest of the build
        # still runs (canonical_ingredient just returns None for everything),
        # which is the right behavior for someone who hasn't authored the
        # file yet.
        logger.warning("ingredients.yaml not found; ontology is empty")
        return Ontology(alias_to_id={}, id_to_category={})

    try:
        raw = yaml.safe_load(path.read_text(encoding="utf-8")) or {}
    except yaml.YAMLError as e:
        raise ValueError(f"ingredients.yaml: invalid YAML: {e}") from e

    entries = raw.get("ingredients", [])

    alias_to_id: dict[str, str] = {}
    id_to_category: dict[str, str] = {}

    for entry in entries:
        ingredient_id = entry["id"]
        category = entry["category"]
        aliases = entry.get("aliases", [])

        if slugify(ingredient_id) != ingredient_id:
            raise ValueError(
                f"ingredients.yaml: id {ingredient_id!r} is not a clean slug "
                f"(slugify produces {slugify(ingredient_id)!r})"
            )
        if category not in CATEGORIES:
            raise ValueError(
                f"ingredients.yaml: id {ingredient_id!r} has unknown category "
                f"{category!r}; allowed: {sorted(CATEGORIES)}"
            )
        if ingredient_id in id_to_category:
            raise ValueError(f"ingredients.yaml: duplicate id {ingredient_id!r}")
        id_to_category[ingredient_id] = category

        for alias in aliases:
            key = _normalize(alias)
            if key in alias_to_id:
                raise ValueError(
                    f"ingredients.yaml: alias {alias!r} (normalized {key!r}) "
                    f"appears under both {alias_to_id[key]!r} and {ingredient_id!r}"
                )
            alias_to_id[key] = ingredient_id

    # Self-alias every canonical id (after the duplicate-check on authored
    # aliases) so canonical_ingredient(canonical_ingredient(x)) is idempotent.
    # Without this, canonical_ingredient("lime-juice") returns None even
    # though "lime-juice" is a valid id.
    for ingredient_id in id_to_category:
        alias_to_id.setdefault(ingredient_id, ingredient_id)

    return Ontology(alias_to_id=alias_to_id, id_to_category=id_to_category)


def canonical_ingredient(name: str | None) -> str | None:
    """Return the canonical id for a raw ingredient name, or None when the
    ingredient isn't in the ontology. None lets callers preserve the raw
    string for display while still being able to dedup on the canonical id
    when it exists."""
    if not name:
        return None
    return _load().alias_to_id.get(_normalize(name))


def category_of(canonical_id: str) -> str | None:
    """Return the category for a canonical id, or None when the id is unknown
    (e.g., the caller is checking an arbitrary string)."""
    return _load().id_to_category.get(canonical_id)


def all_ids() -> list[str]:
    """Sorted list of every canonical id in the ontology — useful for
    coverage reports and faceting."""
    return _load().ids


def reset_cache() -> None:
    """Drop the cached ontology. Tests use this to swap in a stub
    ingredients.yaml without polluting subsequent test runs."""
    _load.cache_clear()
