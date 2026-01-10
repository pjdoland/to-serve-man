"""
Static site generator for To Serve Man cookbook.

Generates a complete static website from Cooklang recipes.
"""

import os
import re
import shutil
import json
from pathlib import Path
from typing import Dict, List
from jinja2 import Environment, FileSystemLoader
from slugify import slugify
import markdown

from recipe_parser import RecipeCollection, Recipe
import config


class SiteGenerator:
    """Generates static website from recipes."""

    def __init__(self, recipes_dir: str = None, output_dir: str = None, base_url: str = None):
        self.recipes_dir = Path(recipes_dir or config.RECIPES_DIR)
        self.output_dir = Path(output_dir or config.DOCS_DIR)
        self.base_url = (base_url if base_url is not None else config.BASE_URL).rstrip('/')
        self.content_dir = Path(config.CONTENT_DIR)

        # Set up Jinja2 environment
        self.jinja_env = Environment(
            loader=FileSystemLoader(config.TEMPLATES_DIR),
            autoescape=True
        )

        # Markdown processor
        self.md = markdown.Markdown(extensions=['extra', 'nl2br'])

        # Load recipes
        self.collection = RecipeCollection(self.recipes_dir)
        self.collection.load_recipes(use_cooklang_parser=False)

    def load_markdown_content(self, filename: str) -> str:
        """Load and convert markdown content to HTML."""
        filepath = self.content_dir / filename
        if filepath.exists():
            with open(filepath, 'r', encoding='utf-8') as f:
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

    def render_template(self, template_name: str, context: Dict, output_path: Path):
        """Render a Jinja2 template and write to file."""
        template = self.jinja_env.get_template(template_name)

        # Add site configuration to all contexts
        context['base_url'] = self.base_url
        context['site_title'] = config.COOKBOOK_TITLE
        context['site_description'] = config.COOKBOOK_DESCRIPTION
        context['site_author'] = config.COOKBOOK_AUTHOR
        context['site_url'] = config.SITE_URL

        html = template.render(**context)

        # Ensure output directory exists
        output_path.parent.mkdir(parents=True, exist_ok=True)

        # Write file
        with open(output_path, 'w', encoding='utf-8') as f:
            f.write(html)

    def parse_recipe_content(self, recipe: Recipe) -> tuple:
        """
        Parse recipe content into HTML-ready ingredients and instructions.

        Returns:
            Tuple of (ingredients_html, instructions_html)
        """
        # Extract content after frontmatter
        content = re.sub(r'^---\s*\n.*?\n---\s*\n', '', recipe.raw_content, flags=re.DOTALL)

        # Split into lines
        lines = content.strip().split('\n')

        ingredients = []
        instructions = []
        current_section = None

        for line in lines:
            line = line.strip()

            # Skip empty lines and comments
            if not line or line.startswith('--'):
                continue

            # Check for section headers
            if line.startswith('>>'):
                current_section = line[2:].strip()
                instructions.append(f'<h3 class="section-header">{current_section}</h3>')
                continue

            # Extract ingredients from the line using proper patterns
            ingredient_pattern = r'@([^{@#~\s]+(?:\s+[^{@#~\s]+)*)\{([^}]*)\}'
            cookware_pattern = r'#(\w+)(?:\{([^}]*)\})?'
            timer_pattern = r'~\{([^}]+)\}'

            # This is an instruction line - process Cooklang syntax
            instruction_html = line

            # Replace ingredients: @ingredient{quantity} -> <span>ingredient</span>
            def replace_ingredient(match):
                return f'<span class="ingredient">{match.group(1)}</span>'
            instruction_html = re.sub(
                r'@([^{@#~\s]+(?:\s+[^{@#~\s]+)*)(?:\{[^}]*\})?',
                replace_ingredient,
                instruction_html
            )

            # Replace cookware: #item or #item{} -> <span>item</span>
            def replace_cookware(match):
                return f'<span class="cookware">{match.group(1)}</span>'
            instruction_html = re.sub(
                r'#(\w+)(?:\{[^}]*\})?',
                replace_cookware,
                instruction_html
            )

            # Replace timers: ~{time} -> <span>time</span> (with % replaced by space)
            def replace_timer(match):
                time_value = match.group(1).replace('%', ' ')
                return f'<span class="timer">{time_value}</span>'
            instruction_html = re.sub(
                timer_pattern,
                replace_timer,
                instruction_html
            )

            instructions.append(instruction_html)

            # Extract ingredients for ingredients list
            for match in re.finditer(ingredient_pattern, line):
                ingredient_name = match.group(1).strip()
                ingredient_quantity = match.group(2).strip() if match.group(2) else ''

                if ingredient_quantity:
                    # Replace % with space in quantities
                    qty_clean = ingredient_quantity.replace('%', ' ')
                    ingredients.append(f"{ingredient_name} ({qty_clean})")
                else:
                    ingredients.append(ingredient_name)

        # Remove duplicates from ingredients while preserving order
        seen = set()
        unique_ingredients = []
        for ing in ingredients:
            # Normalize for comparison
            ing_base = re.sub(r'\([^)]*\)', '', ing).strip().lower()
            if ing_base not in seen:
                seen.add(ing_base)
                unique_ingredients.append(ing)

        # Format ingredients as HTML
        ingredients_html = '<ul>\n' + '\n'.join(f'<li>{ing}</li>' for ing in unique_ingredients) + '\n</ul>'

        # Format instructions as HTML with proper section handling
        instructions_parts = []
        current_section_steps = []

        for item in instructions:
            if item.startswith('<h3'):
                # This is a section header
                # Close previous section if exists
                if current_section_steps:
                    instructions_parts.append('<ol>')
                    instructions_parts.extend(f'<li>{step}</li>' for step in current_section_steps)
                    instructions_parts.append('</ol>')
                    current_section_steps = []

                # Add section header
                instructions_parts.append(item)
            else:
                # This is a regular step
                current_section_steps.append(item)

        # Close final section
        if current_section_steps:
            instructions_parts.append('<ol>')
            instructions_parts.extend(f'<li>{step}</li>' for step in current_section_steps)
            instructions_parts.append('</ol>')

        instructions_html = '\n'.join(instructions_parts)

        return ingredients_html, instructions_html

    def generate_recipe_page(self, recipe: Recipe):
        """Generate individual recipe page."""
        # Parse recipe content
        ingredients_html, instructions_html = self.parse_recipe_content(recipe)

        context = {
            'recipe': recipe,
            'ingredients_html': ingredients_html,
            'instructions_html': instructions_html,
        }

        output_path = self.output_dir / "recipes" / recipe.slug / "index.html"
        self.render_template('recipe.html', context, output_path)

    def generate_homepage(self):
        """Generate homepage."""
        hero_content = self.load_markdown_content('hero.md')

        context = {
            'recipes': self.collection.recipes,
            'categories': self.collection.get_by_category(),
            'tags': self.collection.get_by_tag(),
            'cuisines': self.collection.get_by_cuisine(),
            'spirits': self.collection.get_by_spirit(),
            'hero_content': hero_content,
            'is_homepage': True,
        }

        output_path = self.output_dir / "index.html"
        self.render_template('index.html', context, output_path)

    def generate_list_page(self, title: str, recipes: List[Recipe], output_path: Path, subtitle: str = None):
        """Generate a list page (category, tag, etc.)."""
        context = {
            'title': title,
            'subtitle': subtitle,
            'recipes': recipes,
        }

        self.render_template('list.html', context, output_path)

    def generate_category_pages(self):
        """Generate pages for each category."""
        categories = self.collection.get_by_category()

        for category, recipes in categories.items():
            title = category.replace('-', ' ').title()
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

    def generate_about_page(self):
        """Generate about page."""
        about_content = self.load_markdown_content('about.md')

        context = {
            'about_content': about_content,
        }
        output_path = self.output_dir / "about" / "index.html"
        self.render_template('about.html', context, output_path)

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
        search_data = {'recipes': []}

        for recipe in self.collection.recipes:
            recipe_data = {
                'title': recipe.title,
                'slug': recipe.slug,
                'description': recipe.description or '',
                'tags': recipe.tags,
                'category': recipe.category,
                'is_cocktail': recipe.is_cocktail,
                'url': f'{self.base_url}/recipes/{recipe.slug}/'
            }

            if recipe.is_cocktail:
                recipe_data['spirit_base'] = recipe.spirit_base or ''
            else:
                recipe_data['cuisine'] = recipe.cuisine or ''

            search_data['recipes'].append(recipe_data)

        output_path = self.output_dir / 'search-data.json'
        with open(output_path, 'w', encoding='utf-8') as f:
            json.dump(search_data, f, ensure_ascii=False, indent=2)

    def generate_all(self):
        """Generate complete static site."""
        print("Generating site...")

        # Clean and prepare output directory
        print("  Cleaning output directory...")
        self.clean_output_dir()

        # Copy static files
        print("  Copying static files...")
        self.copy_static_files()

        # Generate homepage
        print("  Generating homepage...")
        self.generate_homepage()

        # Generate search data
        print("  Generating search data...")
        self.generate_search_data()

        # Generate recipe pages
        print(f"  Generating {len(self.collection.recipes)} recipe pages...")
        for recipe in self.collection.recipes:
            self.generate_recipe_page(recipe)

        # Generate category pages
        print("  Generating category pages...")
        self.generate_category_pages()

        # Generate tag pages
        print("  Generating tag pages...")
        self.generate_tag_pages()

        # Generate cuisine pages
        print("  Generating cuisine pages...")
        self.generate_cuisine_pages()

        # Generate spirit pages
        print("  Generating spirit pages...")
        self.generate_spirit_pages()

        # Generate about page
        print("  Generating about page...")
        self.generate_about_page()

        # Generate food and cocktails pages
        print("  Generating food and cocktails pages...")
        self.generate_food_page()
        self.generate_cocktails_page()

        print(f"✓ Site generated successfully in {self.output_dir}/")


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
