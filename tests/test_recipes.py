"""Smoke tests: every recipe must parse, validate, render to HTML, and render to LaTeX."""

import json
import tempfile
import unittest
from pathlib import Path

from pdf_generator import PDFGenerator
from recipe_parser import RecipeCollection
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

    def test_search_data_includes_ingredients(self):
        with tempfile.TemporaryDirectory() as tmp:
            self.site.output_dir = Path(tmp)
            self.site.generate_search_data()
            data = json.loads((Path(tmp) / "search-data.json").read_text())
        # Every recipe carries an ingredients list (may be empty for headnote-only entries).
        for entry in data["recipes"]:
            self.assertIn("ingredients", entry)
            self.assertIsInstance(entry["ingredients"], list)
        # Sanity: at least one recipe has ingredients (otherwise the field is
        # decorative and the search-by-ingredient feature is broken).
        self.assertTrue(
            any(entry["ingredients"] for entry in data["recipes"]),
            "no recipe in the search index has any ingredients — feature is dead",
        )


class LoadFailureGate(unittest.TestCase):
    """Pin the contract that a malformed .cook file populates load_errors so
    build_site / build_pdf / build_latex can fail-fast on parse failures."""

    def test_yaml_syntax_error_populates_load_errors(self):
        with tempfile.TemporaryDirectory() as tmp:
            recipes_dir = Path(tmp)
            (recipes_dir / "broken.cook").write_text(
                "---\ntitle: Broken\ntags: [unclosed\n---\nStir.\n",
                encoding="utf-8",
            )
            collection = RecipeCollection(recipes_dir)
            collection.load_recipes()
            self.assertEqual(len(collection.load_errors), 1)
            failed_path, _msg = collection.load_errors[0]
            self.assertEqual(failed_path.name, "broken.cook")
            self.assertEqual(collection.recipes, [])


class CrossRefFailureTracking(unittest.TestCase):
    """Pin that an unknown serve_with/pairs_with/uses slug populates
    SiteGenerator.cross_ref_failures so build.py --strict can fail on it."""

    def test_unknown_slug_recorded(self):
        with tempfile.TemporaryDirectory() as tmp:
            recipes_dir = Path(tmp)
            (recipes_dir / "host.cook").write_text(
                "---\ntitle: Host\nserve_with: [does-not-exist]\n---\nStir.\n",
                encoding="utf-8",
            )
            site = SiteGenerator(recipes_dir=str(recipes_dir), output_dir=tmp)
            host = site.collection.recipes[0]
            site._resolve_cross_refs(host)
            self.assertEqual(len(site.cross_ref_failures), 1)
            _filepath, field, slug = site.cross_ref_failures[0]
            self.assertEqual(field, "serve_with")
            self.assertEqual(slug, "does-not-exist")


if __name__ == "__main__":
    unittest.main()
