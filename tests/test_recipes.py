"""Smoke tests: every recipe must parse, validate, render to HTML, and render to LaTeX."""

import json
import tempfile
import unittest
from pathlib import Path

from pdf_generator import PDFGenerator
from site_generator import SiteGenerator


class RecipeSmokeTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.site = SiteGenerator()
        cls.pdf = PDFGenerator()
        cls.recipes = cls.site.collection.recipes

    def test_recipes_loaded(self):
        self.assertGreater(len(self.recipes), 0, "no recipes were loaded")

    def test_all_recipes_validate(self):
        errors = self.site.collection.validate_all()
        self.assertEqual(errors, {}, f"validation errors: {errors}")

    def test_site_renders_every_recipe(self):
        for recipe in self.recipes:
            with self.subTest(recipe=recipe.filepath.name):
                _, _, instructions_html, _ = self.site.parse_recipe_content(recipe)
                self.assertTrue(instructions_html, f"{recipe.filepath} produced no instructions HTML")

    def test_pdf_latex_renders_every_recipe(self):
        for recipe in self.recipes:
            with self.subTest(recipe=recipe.filepath.name):
                latex = self.pdf.format_recipe_latex(recipe)
                self.assertIn("\\section{", latex, f"{recipe.filepath} missing \\section header")

    def test_full_latex_document_builds(self):
        latex = self.pdf.generate_latex()
        self.assertIn("\\begin{document}", latex)
        self.assertIn("\\end{document}", latex)

    def test_search_data_includes_every_recipe(self):
        with tempfile.TemporaryDirectory() as tmp:
            self.site.output_dir = Path(tmp)
            self.site.generate_search_data()
            data = json.loads((Path(tmp) / "search-data.json").read_text())
        self.assertEqual(len(data["recipes"]), len(self.recipes))


if __name__ == "__main__":
    unittest.main()
