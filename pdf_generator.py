"""
PDF cookbook generator for To Serve Man.

Generates a beautifully typeset LaTeX cookbook and compiles it to PDF.
"""

import logging
import subprocess
from pathlib import Path

import config
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
)

logger = logging.getLogger("tsm.pdf")


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
            "&": r"\&",
            "%": r"\%",
            "$": r"\$",
            "#": r"\#",
            "_": r"\_",
            "{": r"\{",
            "}": r"\}",
            "~": r"\textasciitilde{}",
            "^": r"\^{}",
            "\\": r"\textbackslash{}",
        }

        for char, replacement in replacements.items():
            text = text.replace(char, replacement)

        return text

    def parse_recipe_content(self, recipe: Recipe) -> tuple[list[str], list[Section | Callout | str]]:
        """Render the recipe body to (ingredients_latex, blocks).

        Each block is a `Section` (header), a `Callout` (typed kind+text),
        or a plain LaTeX-escaped string (a step).
        """
        parsed = recipe.parsed

        unique_ingredients: list[str] = []
        for ing in parsed.ingredients:
            if not ing.from_braces:
                continue
            name_latex = self.escape_latex(ing.name)
            qty = ing.qty_display
            if qty:
                unique_ingredients.append(f"\\textbf{{{name_latex}}} -- {self.escape_latex(qty)}")
            else:
                unique_ingredients.append(f"\\textbf{{{name_latex}}}")

        blocks: list[Section | Callout | str] = []
        for block in parsed.blocks:
            if isinstance(block, (Section, Callout)):
                blocks.append(block)
            else:
                blocks.append(self._render_step_latex(block))

        return unique_ingredients, blocks

    def _render_step_latex(self, step: Step) -> str:
        """Render a step to plain LaTeX text — Cooklang markers stripped, special chars escaped."""
        out: list[str] = []
        for tok in step.tokens:
            if isinstance(tok, Text):
                out.append(self.escape_latex(tok.text))
            elif isinstance(tok, (Ingredient, Cookware)):
                out.append(self.escape_latex(tok.name))
            elif isinstance(tok, Timer):
                out.append(self.escape_latex(tok.display))
        return "".join(out)

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
            if recipe.garnish and recipe.garnish.lower() != "none":
                meta_parts.append(f"Garnish: {recipe.garnish}")
        else:
            if recipe.servings:
                meta_parts.append(f"{recipe.servings} servings")
            if recipe.prep_time:
                meta_parts.append(f"{recipe.prep_time} prep")
            if recipe.cook_time:
                meta_parts.append(f"{recipe.cook_time} cook")

        if meta_parts:
            # Use interpunct (·) for metadata separators
            escaped_parts = [self.escape_latex(part) for part in meta_parts]
            meta_string = " · ".join(escaped_parts)
            latex.append(f"\\recipemeta{{{meta_string}}}")

        # Description
        if recipe.description:
            latex.append(f"\\recipedescription{{{self.escape_latex(recipe.description)}}}")

        # Headnote (cook's voice / story)
        if recipe.headnote:
            latex.append(f"\\recipeheadnote{{{self.escape_latex(recipe.headnote)}}}")

        # Parse content
        ingredients, blocks = self.parse_recipe_content(recipe)

        # Ingredients section
        if ingredients:
            latex.append("\\subsection*{Ingredients}")
            latex.append("\\begin{ingredients}")
            for ingredient in ingredients:
                latex.append(f"\\item {ingredient}")
            latex.append("\\end{ingredients}")

        # Instructions section
        if blocks:
            latex.append("\\subsection*{Instructions}")

            # Group steps under their preceding section; callouts break the group.
            current_section_items: list[str] = []

            def flush_steps():
                if current_section_items:
                    latex.append("\\begin{enumerate}")
                    for step in current_section_items:
                        latex.append(f"\\item {step}")
                    latex.append("\\end{enumerate}")
                    current_section_items.clear()

            for block in blocks:
                if isinstance(block, Section):
                    flush_steps()
                    latex.append(f"\\subsubsection*{{{self.escape_latex(block.name)}}}")
                elif isinstance(block, Callout):
                    flush_steps()
                    latex.append(f"\\callout{{{block.kind}}}{{{self.escape_latex(block.text)}}}")
                else:
                    current_section_items.append(block)

            flush_steps()

        # Phase 3: storage / make-ahead / yield notes / variations
        notes_lines: list[str] = []
        for field_name, label in RECIPE_NOTE_FIELDS:
            value = getattr(recipe, field_name)
            if value:
                notes_lines.append(f"\\textbf{{{label}:}} {self.escape_latex(value)}")
        if notes_lines:
            latex.append("\\recipenotes{" + " \\\\ ".join(notes_lines) + "}")

        if recipe.variations:
            latex.append("\\subsection*{Variations}")
            latex.append("\\begin{ingredients}")
            for v in recipe.variations:
                name = self.escape_latex(v.get("name", ""))
                swap = self.escape_latex(v.get("swap", ""))
                note = self.escape_latex(v.get("note", ""))
                bits = [b for b in (swap, note) if b]
                latex.append(f"\\item \\textbf{{{name}}}" + (f" -- {' — '.join(bits)}" if bits else ""))
            latex.append("\\end{ingredients}")

        # Attribution - \recipeattribution already adds "Recipe by" prefix
        if recipe.metadata.get("author") or recipe.metadata.get("adapted_by"):
            attr_parts = []
            if recipe.metadata.get("author"):
                attr_parts.append(recipe.metadata["author"])
            if recipe.metadata.get("adapted_by"):
                attr_parts.append(f"adapted by {recipe.metadata['adapted_by']}")
            # First part is author, rest are adaptations
            attr_string = ", ".join(attr_parts)
            latex.append(f"\\recipeattribution{{Recipe by {self.escape_latex(attr_string)}}}")

        # Add vertical space between recipes instead of forcing page breaks
        latex.append("\\vspace{3\\baselineskip}")

        return "\n".join(latex)

    def generate_latex(self) -> str:
        """
        Generate complete LaTeX document.

        Returns:
            Complete LaTeX document as string
        """
        latex_parts = []

        # Read preamble and replace placeholders
        preamble_file = self.latex_dir / "preamble.tex"
        with open(preamble_file, encoding="utf-8") as f:
            preamble = f.read()

        # Replace title placeholder with lowercase version (small caps will uppercase it)
        preamble = preamble.replace("{{COOKBOOK_TITLE_LOWER}}", self.escape_latex(self.pdf_title.lower()))

        # Replace author placeholder - only add author line if author is set
        if self.pdf_author:
            author_line = f"{{\\large {self.escape_latex(self.pdf_author)}}}\\\\[1em]\n"
        else:
            author_line = ""
        preamble = preamble.replace("{{COOKBOOK_AUTHOR_LINE}}", author_line)

        latex_parts.append(preamble)

        # Part I: Food Recipes
        food_recipes = self.collection.food_recipes
        if food_recipes:
            latex_parts.append("\n\\part{Food}\n")

            # Group by category, then output in canonical order
            categories: dict[str, list[Recipe]] = {}
            for recipe in food_recipes:
                categories.setdefault(recipe.category, []).append(recipe)

            for category in config.order_food_categories(list(categories.keys())):
                recipes = categories[category]
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
        with open(closing_file, encoding="utf-8") as f:
            latex_parts.append(f.read())

        return "\n".join(latex_parts)

    def write_latex(self) -> Path:
        """Generate LaTeX source and write it to disk. Returns the .tex path."""
        self.output_dir.mkdir(parents=True, exist_ok=True)
        tex_file = self.output_dir / "cookbook.tex"
        tex_file.write_text(self.generate_latex(), encoding="utf-8")
        return tex_file

    def compile_pdf(self) -> bool:
        """
        Compile cookbook.tex to PDF using pdflatex.

        Clears stale aux/toc so a previous broken build can't poison this one
        with undefined references. Runs pdflatex twice so the TOC resolves.
        """
        for ext in ("aux", "toc", "out", "log"):
            (self.output_dir / f"cookbook.{ext}").unlink(missing_ok=True)

        try:
            for i in range(2):
                result = subprocess.run(
                    ["pdflatex", "-interaction=nonstopmode", "cookbook.tex"],
                    cwd=self.output_dir,
                    capture_output=True,
                    text=True,
                    timeout=120,
                )
                if result.returncode != 0 and not (self.output_dir / "cookbook.pdf").exists():
                    logger.error(f"Error compiling LaTeX (run {i + 1}):")
                    logger.info(result.stdout)
                    return False

            return True

        except FileNotFoundError:
            logger.error(
                "Error: pdflatex not found. Please install a LaTeX distribution (e.g., TeX Live, MiKTeX)."
            )
            return False
        except subprocess.TimeoutExpired:
            logger.error("Error: LaTeX compilation timed out.")
            return False

    def generate_all(self):
        """Generate complete PDF cookbook."""
        logger.info("Generating PDF cookbook...")

        logger.info("  Generating LaTeX...")
        tex_file = self.write_latex()
        logger.info(f"  LaTeX written to {tex_file}")

        logger.info("  Compiling PDF...")
        if self.compile_pdf():
            logger.info(f"✓ PDF generated successfully: {self.output_dir / 'cookbook.pdf'}")
        else:
            logger.error("✗ PDF compilation failed. LaTeX source is available at:", tex_file)


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
