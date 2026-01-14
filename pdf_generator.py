"""
PDF cookbook generator for To Serve Man.

Generates a beautifully typeset LaTeX cookbook and compiles it to PDF.
"""

import os
import re
import subprocess
from pathlib import Path
from typing import Dict, List

from recipe_parser import RecipeCollection, Recipe
import config


class PDFGenerator:
    """Generates PDF cookbook from recipes."""

    def __init__(self, recipes_dir: str = None, output_dir: str = None):
        self.recipes_dir = Path(recipes_dir or config.RECIPES_DIR)
        self.output_dir = Path(output_dir or config.OUTPUT_DIR)
        self.latex_dir = Path(config.LATEX_DIR)
        self.pdf_title = config.PDF_TITLE
        self.pdf_author = config.PDF_AUTHOR

        # Load recipes
        self.collection = RecipeCollection(self.recipes_dir)
        self.collection.load_recipes(use_cooklang_parser=False)

    def escape_latex(self, text: str) -> str:
        """
        Escape special LaTeX characters.

        Args:
            text: Raw text string

        Returns:
            LaTeX-safe string
        """
        if not text:
            return ""

        # Replace special characters
        replacements = {
            '&': r'\&',
            '%': r'\%',
            '$': r'\$',
            '#': r'\#',
            '_': r'\_',
            '{': r'\{',
            '}': r'\}',
            '~': r'\textasciitilde{}',
            '^': r'\^{}',
            '\\': r'\textbackslash{}',
        }

        for char, replacement in replacements.items():
            text = text.replace(char, replacement)

        return text

    def parse_recipe_content(self, recipe: Recipe) -> tuple:
        """
        Parse recipe content into LaTeX-ready ingredients and instructions.

        Returns:
            Tuple of (ingredients_list, instructions_list)
        """
        # Extract content after frontmatter
        content = re.sub(r'^---\s*\n.*?\n---\s*\n', '', recipe.raw_content, flags=re.DOTALL)

        # Split into lines
        lines = content.strip().split('\n')

        ingredients_dict = {}  # Use dict to track unique ingredients
        instructions = []

        for line in lines:
            line = line.strip()

            # Skip empty lines and comments
            if not line or line.startswith('--'):
                continue

            # Check for section headers
            if line.startswith('>>'):
                section_name = line[2:].strip()
                instructions.append(('section', section_name))
                continue

            # Extract ingredients from this line for the ingredients list
            # Pattern matches: @ingredient{quantity} or @ingredient{}
            for match in re.finditer(r'@([^{@#~]+)\{([^}]*)\}', line):
                ing_name = match.group(1).strip()
                ing_qty = match.group(2).strip()

                # Store in dict (will deduplicate automatically)
                if ing_name.lower() not in ingredients_dict:
                    if ing_qty:
                        # Clean up quantity: replace % with space
                        qty_clean = ing_qty.replace('%', ' ')
                        ingredients_dict[ing_name.lower()] = f"{ing_name} ({qty_clean})"
                    else:
                        ingredients_dict[ing_name.lower()] = ing_name

            # Clean the instruction text by removing all Cooklang markup
            instruction_text = line

            # Replace Cooklang markers with plain text (do this BEFORE LaTeX escaping)
            # Ingredients: @ingredient{quantity} -> ingredient
            instruction_text = re.sub(r'@(\w+(?:\s+\w+)*)(?:\{[^}]*\})?', r'\1', instruction_text)

            # Cookware: #item or #item{} or #item{quantity} -> item
            instruction_text = re.sub(r'#(\w+)(?:\{[^}]*\})?', r'\1', instruction_text)

            # Timers: ~{time} -> time (replace % with space)
            def clean_timer(match):
                return match.group(1).replace('%', ' ')
            instruction_text = re.sub(r'~\{([^}]+)\}', clean_timer, instruction_text)

            # Clean up any remaining empty braces or orphaned symbols
            instruction_text = re.sub(r'\{\}', '', instruction_text)
            instruction_text = re.sub(r'[@#~]\s*', '', instruction_text)  # Remove orphaned markers

            # Escape LaTeX special characters AFTER all Cooklang cleanup
            instruction_text = self.escape_latex(instruction_text)

            instructions.append(('step', instruction_text))

        # Convert ingredients dict to list and escape for LaTeX
        unique_ingredients = []
        for ing_name_lower, ing_display in ingredients_dict.items():
            unique_ingredients.append(self.escape_latex(ing_display))

        return unique_ingredients, instructions

    def format_recipe_latex(self, recipe: Recipe) -> str:
        """
        Format a single recipe as LaTeX.

        Args:
            recipe: Recipe object

        Returns:
            LaTeX string for the recipe
        """
        latex = []

        # Prevent awkward page breaks (require at least 4 baseline skips available)
        latex.append("\\needspace{4\\baselineskip}")

        # Recipe title as section
        latex.append(f"\\section{{{self.escape_latex(recipe.title)}}}")

        # Metadata
        meta_parts = []
        if recipe.is_cocktail:
            if recipe.glass:
                meta_parts.append(recipe.glass.title())
            if recipe.spirit_base:
                meta_parts.append(recipe.spirit_base.title())
            if recipe.garnish and recipe.garnish.lower() != 'none':
                meta_parts.append(f"Garnish: {recipe.garnish}")
        else:
            if recipe.servings:
                meta_parts.append(f"{recipe.servings} servings")
            if recipe.prep_time:
                meta_parts.append(f"{recipe.prep_time} prep")
            if recipe.cook_time:
                meta_parts.append(f"{recipe.cook_time} cook")

        if meta_parts:
            # Use \quad for elegant spacing between metadata items
            escaped_parts = [self.escape_latex(part) for part in meta_parts]
            meta_string = ' \\quad '.join(escaped_parts)
            latex.append(f"\\recipemeta{{{meta_string}}}")

        # Description
        if recipe.description:
            latex.append(f"\\recipedescription{{{self.escape_latex(recipe.description)}}}")

        # Parse content
        ingredients, instructions = self.parse_recipe_content(recipe)

        # Ingredients section
        if ingredients:
            latex.append("{\\ingredientsheading Ingredients}\\par")
            latex.append("\\begin{ingredients}")
            for ingredient in ingredients:
                latex.append(f"\\item {ingredient}")
            latex.append("\\end{ingredients}")

        # Instructions section
        if instructions:
            latex.append("\\vspace{0.75\\baselineskip}")  # Space between sections
            latex.append("{\\instructionsheading Instructions}\\par")

            # Group by sections
            current_section_items = []
            for item_type, item_content in instructions:
                if item_type == 'section':
                    # Output previous section if exists
                    if current_section_items:
                        latex.append("\\begin{enumerate}")
                        for step in current_section_items:
                            latex.append(f"\\item {step}")
                        latex.append("\\end{enumerate}")
                        current_section_items = []

                    # Add new section header
                    latex.append(f"\\subsection*{{{self.escape_latex(item_content)}}}")
                else:
                    current_section_items.append(item_content)

            # Output final section
            if current_section_items:
                latex.append("\\begin{enumerate}")
                for step in current_section_items:
                    latex.append(f"\\item {step}")
                latex.append("\\end{enumerate}")

        # Attribution
        if recipe.metadata.get('author') or recipe.metadata.get('adapted_by'):
            attr_parts = []
            if recipe.metadata.get('author'):
                attr_parts.append(f"Recipe by {recipe.metadata['author']}")
            if recipe.metadata.get('adapted_by'):
                attr_parts.append(f"adapted by {recipe.metadata['adapted_by']}")
            latex.append(f"\\recipeattribution{{{self.escape_latex(', '.join(attr_parts))}}}")

        latex.append("\\clearpage")

        return '\n'.join(latex)

    def generate_latex(self) -> str:
        """
        Generate complete LaTeX document.

        Returns:
            Complete LaTeX document as string
        """
        latex_parts = []

        # Read preamble and replace placeholders
        preamble_file = self.latex_dir / "preamble.tex"
        with open(preamble_file, 'r', encoding='utf-8') as f:
            preamble = f.read()

        # Replace title placeholder
        preamble = preamble.replace('{{COOKBOOK_TITLE}}', self.escape_latex(self.pdf_title))

        # Replace author placeholder - only add author line if author is set
        if self.pdf_author:
            author_line = f'{{\\large {self.escape_latex(self.pdf_author)}}}\\\\[1em]\n'
        else:
            author_line = ''
        preamble = preamble.replace('{{COOKBOOK_AUTHOR_LINE}}', author_line)

        latex_parts.append(preamble)

        # Part I: Food Recipes
        food_recipes = self.collection.food_recipes
        if food_recipes:
            latex_parts.append("\n\\part{Food}\n")

            # Group by category
            categories = {}
            for recipe in food_recipes:
                if recipe.category not in categories:
                    categories[recipe.category] = []
                categories[recipe.category].append(recipe)

            # Sort categories
            category_order = ['breakfast', 'basics', 'mains', 'sides', 'desserts']
            sorted_categories = []
            for cat in category_order:
                if cat in categories:
                    sorted_categories.append((cat, categories[cat]))
            # Add any remaining categories
            for cat, recipes in categories.items():
                if cat not in category_order:
                    sorted_categories.append((cat, recipes))

            # Output each category as a chapter
            for category, recipes in sorted_categories:
                latex_parts.append(f"\n\\chapter{{{category.replace('-', ' ').title()}}}\n")
                for recipe in sorted(recipes, key=lambda r: r.title):
                    latex_parts.append(self.format_recipe_latex(recipe))

        # Part II: Cocktails
        cocktail_recipes = self.collection.cocktail_recipes
        if cocktail_recipes:
            latex_parts.append("\n\\part{Cocktails}\n")
            latex_parts.append("\n\\chapter{Cocktails}\n")

            # Sort by spirit base, then by name
            spirits = self.collection.get_by_spirit()
            for spirit in sorted(spirits.keys()):
                recipes = spirits[spirit]
                for recipe in sorted(recipes, key=lambda r: r.title):
                    latex_parts.append(self.format_recipe_latex(recipe))

        # Read closing
        closing_file = self.latex_dir / "closing.tex"
        with open(closing_file, 'r', encoding='utf-8') as f:
            latex_parts.append(f.read())

        return '\n'.join(latex_parts)

    def compile_pdf(self, tex_file: Path) -> bool:
        """
        Compile LaTeX to PDF using pdflatex.

        Args:
            tex_file: Path to .tex file

        Returns:
            True if successful, False otherwise
        """
        try:
            # Run pdflatex twice for TOC
            for i in range(2):
                result = subprocess.run(
                    ['pdflatex', '-interaction=nonstopmode', str(tex_file)],
                    cwd=self.output_dir,
                    capture_output=True,
                    text=True,
                    timeout=60
                )

                if result.returncode != 0:
                    # Check if PDF was still generated despite errors
                    pdf_file = self.output_dir / "cookbook.pdf"
                    if not pdf_file.exists():
                        print(f"Error compiling LaTeX (run {i+1}):")
                        print(result.stdout)
                        return False
                    # PDF exists, so continue even with warnings

            return True

        except FileNotFoundError:
            print("Error: pdflatex not found. Please install a LaTeX distribution (e.g., TeX Live, MiKTeX).")
            return False
        except subprocess.TimeoutExpired:
            print("Error: LaTeX compilation timed out.")
            return False
        except Exception as e:
            print(f"Error compiling LaTeX: {e}")
            return False

    def generate_all(self):
        """Generate complete PDF cookbook."""
        print("Generating PDF cookbook...")

        # Create output directory
        self.output_dir.mkdir(parents=True, exist_ok=True)

        # Generate LaTeX
        print("  Generating LaTeX...")
        latex_content = self.generate_latex()

        # Write LaTeX file
        tex_file = self.output_dir / "cookbook.tex"
        with open(tex_file, 'w', encoding='utf-8') as f:
            f.write(latex_content)

        print(f"  LaTeX written to {tex_file}")

        # Compile to PDF
        print("  Compiling PDF...")
        if self.compile_pdf("cookbook.tex"):
            pdf_file = self.output_dir / "cookbook.pdf"
            print(f"✓ PDF generated successfully: {pdf_file}")
        else:
            print("✗ PDF compilation failed. LaTeX source is available at:", tex_file)


def generate_pdf(recipes_dir: str = None, output_dir: str = None):
    """
    Convenience function to generate PDF.

    Args:
        recipes_dir: Path to recipes directory (default: from config)
        output_dir: Path to output directory (default: from config)
    """
    generator = PDFGenerator(recipes_dir, output_dir)
    generator.generate_all()


if __name__ == "__main__":
    generate_pdf()
