"""
Recipe parser and validator for To Serve Man cookbook system.

Handles discovery, parsing, and validation of Cooklang recipe files.
"""

import os
import re
from pathlib import Path
from typing import Dict, List, Optional, Any
import yaml
from slugify import slugify


class Recipe:
    """Represents a parsed recipe with metadata and content."""

    def __init__(self, filepath: Path, parsed_data: Dict[str, Any], raw_content: str):
        self.filepath = filepath
        self.parsed_data = parsed_data
        self.raw_content = raw_content

        # Extract metadata from frontmatter
        self.metadata = self._extract_metadata()

        # Determine recipe type
        self.is_cocktail = self.metadata.get('type') == 'cocktail' or 'cocktails' in str(filepath)

        # Generate slug for URLs
        self.slug = slugify(self.metadata.get('title', filepath.stem))

        # Determine category from filepath
        self.category = self._determine_category()

    def _extract_metadata(self) -> Dict[str, Any]:
        """Extract YAML frontmatter from raw content."""
        # Match YAML frontmatter between --- markers
        match = re.match(r'^---\s*\n(.*?)\n---\s*\n', self.raw_content, re.DOTALL)
        if match:
            try:
                return yaml.safe_load(match.group(1)) or {}
            except yaml.YAMLError as e:
                raise ValueError(f"Invalid YAML frontmatter: {e}")
        return {}

    def _determine_category(self) -> str:
        """Determine recipe category from filepath."""
        # Get parent directory name
        return self.filepath.parent.name

    @property
    def title(self) -> str:
        """Get recipe title."""
        return self.metadata.get('title', 'Untitled Recipe')

    @property
    def description(self) -> Optional[str]:
        """Get recipe description."""
        return self.metadata.get('description')

    @property
    def tags(self) -> List[str]:
        """Get recipe tags."""
        return self.metadata.get('tags', [])

    @property
    def cuisine(self) -> Optional[str]:
        """Get cuisine type (food recipes only)."""
        return self.metadata.get('cuisine')

    @property
    def spirit_base(self) -> Optional[str]:
        """Get spirit base (cocktail recipes only)."""
        return self.metadata.get('spirit_base')

    @property
    def difficulty(self) -> Optional[str]:
        """Get difficulty level."""
        return self.metadata.get('difficulty')

    @property
    def servings(self) -> Optional[int]:
        """Get number of servings."""
        servings = self.metadata.get('servings')
        if servings:
            try:
                return int(servings)
            except (ValueError, TypeError):
                return None
        return None

    @property
    def prep_time(self) -> Optional[str]:
        """Get prep time."""
        return self.metadata.get('prep_time')

    @property
    def cook_time(self) -> Optional[str]:
        """Get cook time."""
        return self.metadata.get('cook_time')

    @property
    def glass(self) -> Optional[str]:
        """Get glass type (cocktails only)."""
        return self.metadata.get('glass')

    @property
    def garnish(self) -> Optional[str]:
        """Get garnish (cocktails only)."""
        return self.metadata.get('garnish')

    def validate(self) -> List[str]:
        """
        Validate recipe and return list of errors/warnings.

        Returns:
            List of error/warning messages (empty if valid)
        """
        errors = []

        # Check required fields
        if not self.title or self.title == 'Untitled Recipe':
            errors.append(f"{self.filepath}: Missing required field 'title'")

        # Validate recipe-type-specific fields
        if self.is_cocktail:
            # Cocktail validations
            if not self.spirit_base:
                errors.append(f"{self.filepath}: Cocktail recipes should have 'spirit_base'")
            if not self.glass:
                errors.append(f"{self.filepath}: Cocktail recipes should have 'glass'")
        else:
            # Food recipe validations
            if not self.cuisine:
                errors.append(f"{self.filepath}: Food recipes should have 'cuisine'")

        return errors


class RecipeCollection:
    """Manages a collection of recipes."""

    def __init__(self, recipes_dir: Path):
        self.recipes_dir = Path(recipes_dir)
        self.recipes: List[Recipe] = []
        self._loaded = False

    def discover_recipes(self) -> List[Path]:
        """Discover all .cook files in recipes directory."""
        if not self.recipes_dir.exists():
            raise FileNotFoundError(f"Recipes directory not found: {self.recipes_dir}")

        return list(self.recipes_dir.rglob("*.cook"))

    def load_recipes(self, use_cooklang_parser: bool = False):
        """
        Load and parse all recipes.

        Args:
            use_cooklang_parser: If True, use cooklang-py library for parsing.
                                If False, just extract metadata (faster, no C extension needed).
        """
        recipe_files = self.discover_recipes()

        for recipe_file in recipe_files:
            try:
                # Read raw content
                with open(recipe_file, 'r', encoding='utf-8') as f:
                    raw_content = f.read()

                # Parse with cooklang if requested
                parsed_data = {}
                if use_cooklang_parser:
                    try:
                        import cooklang
                        parsed_data = cooklang.parseRecipe(str(recipe_file))
                    except ImportError:
                        print("Warning: cooklang-py not installed. Falling back to metadata-only parsing.")
                    except Exception as e:
                        print(f"Warning: Failed to parse {recipe_file} with cooklang: {e}")

                # Create Recipe object
                recipe = Recipe(recipe_file, parsed_data, raw_content)
                self.recipes.append(recipe)

            except Exception as e:
                print(f"Error loading recipe {recipe_file}: {e}")

        self._loaded = True
        return self.recipes

    def validate_all(self) -> Dict[str, List[str]]:
        """
        Validate all recipes.

        Returns:
            Dictionary mapping recipe paths to lists of errors
        """
        if not self._loaded:
            self.load_recipes()

        all_errors = {}
        for recipe in self.recipes:
            errors = recipe.validate()
            if errors:
                all_errors[str(recipe.filepath)] = errors

        return all_errors

    def get_by_category(self) -> Dict[str, List[Recipe]]:
        """Group recipes by category."""
        categories = {}
        for recipe in self.recipes:
            category = recipe.category
            if category not in categories:
                categories[category] = []
            categories[category].append(recipe)
        return categories

    def get_by_tag(self) -> Dict[str, List[Recipe]]:
        """Group recipes by tag."""
        tags = {}
        for recipe in self.recipes:
            for tag in recipe.tags:
                if tag not in tags:
                    tags[tag] = []
                tags[tag].append(recipe)
        return tags

    def get_by_cuisine(self) -> Dict[str, List[Recipe]]:
        """Group food recipes by cuisine."""
        cuisines = {}
        for recipe in self.recipes:
            if not recipe.is_cocktail and recipe.cuisine:
                cuisine = recipe.cuisine
                if cuisine not in cuisines:
                    cuisines[cuisine] = []
                cuisines[cuisine].append(recipe)
        return cuisines

    def get_by_spirit(self) -> Dict[str, List[Recipe]]:
        """Group cocktail recipes by spirit base."""
        spirits = {}
        for recipe in self.recipes:
            if recipe.is_cocktail and recipe.spirit_base:
                spirit = recipe.spirit_base
                if spirit not in spirits:
                    spirits[spirit] = []
                spirits[spirit].append(recipe)
        return spirits

    @property
    def food_recipes(self) -> List[Recipe]:
        """Get all food recipes."""
        return [r for r in self.recipes if not r.is_cocktail]

    @property
    def cocktail_recipes(self) -> List[Recipe]:
        """Get all cocktail recipes."""
        return [r for r in self.recipes if r.is_cocktail]


def load_and_parse_recipes(recipes_dir: str = "recipes") -> RecipeCollection:
    """
    Convenience function to load recipes.

    Args:
        recipes_dir: Path to recipes directory

    Returns:
        RecipeCollection with loaded recipes
    """
    collection = RecipeCollection(Path(recipes_dir))
    collection.load_recipes(use_cooklang_parser=False)  # Start with simple parsing
    return collection
