"""Smoke tests: every recipe must parse, validate, render to HTML, and render to LaTeX."""

import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from pdf_generator import PDFGenerator
from recipe_parser import RecipeCollection
from site_generator import SiteGenerator


class RecipeSmokeTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.collection = RecipeCollection("recipes")
        cls.collection.load_recipes(use_cooklang_parser=False)

    def test_recipes_loaded(self):
        self.assertGreater(len(self.collection.recipes), 0, "no recipes were loaded")

    def test_all_recipes_validate(self):
        errors = self.collection.validate_all()
        self.assertEqual(errors, {}, f"validation errors: {errors}")

    def test_every_recipe_has_body(self):
        for recipe in self.collection.recipes:
            with self.subTest(recipe=recipe.filepath.name):
                body = recipe.raw_content[recipe.raw_content.find('---', 3) + 3:].strip()
                self.assertTrue(body, f"{recipe.filepath} has no body after frontmatter")

    def test_site_renders_every_recipe(self):
        site = SiteGenerator()
        for recipe in site.collection.recipes:
            with self.subTest(recipe=recipe.filepath.name):
                ingredients_html, instructions_html = site.parse_recipe_content(recipe)
                self.assertTrue(instructions_html, f"{recipe.filepath} produced no instructions HTML")

    def test_pdf_latex_renders_every_recipe(self):
        pdf = PDFGenerator()
        for recipe in pdf.collection.recipes:
            with self.subTest(recipe=recipe.filepath.name):
                latex = pdf.format_recipe_latex(recipe)
                self.assertIn("\\section{", latex, f"{recipe.filepath} missing \\section header")

    def test_full_latex_document_builds(self):
        latex = PDFGenerator().generate_latex()
        self.assertIn("\\begin{document}", latex)
        self.assertIn("\\end{document}", latex)

    def test_search_data_includes_every_recipe(self):
        site = SiteGenerator()
        site.output_dir = Path("/tmp/tsm-test-out")
        site.output_dir.mkdir(parents=True, exist_ok=True)
        site.generate_search_data()
        import json
        data = json.loads((site.output_dir / "search-data.json").read_text())
        self.assertEqual(len(data["recipes"]), len(site.collection.recipes))


if __name__ == "__main__":
    unittest.main()
