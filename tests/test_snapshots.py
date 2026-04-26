"""Snapshot tests that pin rendered HTML and LaTeX for representative recipes.

Run with `UPDATE_SNAPSHOTS=1 python -m unittest discover -s tests -t .` to refresh
fixtures after an intentional rendering change.
"""

import difflib
import os
import unittest
from pathlib import Path

from pdf_generator import PDFGenerator
from site_generator import SiteGenerator

FIXTURES_DIR = Path(__file__).parent / "fixtures"

# One recipe from each interesting shape:
#   - sections + timers + many ingredients
#   - cocktail with garnish
#   - LaTeX special chars + multiple sections
#   - plain food recipe
#   - bare `>` headnotes (Mai Tai has two before the steps)
SNAPSHOT_RECIPES = [
    "pasta-carbonara",
    "negroni",
    "chocolate-chip-cookies",
    "french-toast",
    "01-mai-tai",
]


def _diff(expected: str, actual: str, label: str) -> str:
    return "\n".join(
        difflib.unified_diff(
            expected.splitlines(),
            actual.splitlines(),
            fromfile=f"{label} (fixture)",
            tofile=f"{label} (rendered)",
            lineterm="",
        )
    )


class SnapshotTests(unittest.TestCase):
    update = os.environ.get("UPDATE_SNAPSHOTS") == "1"

    @classmethod
    def setUpClass(cls):
        cls.site = SiteGenerator()
        cls.pdf = PDFGenerator()
        cls.recipes_by_slug = {r.filepath.stem: r for r in cls.site.collection.recipes}
        FIXTURES_DIR.mkdir(exist_ok=True)

    def _check(self, slug: str, suffix: str, actual: str):
        fixture = FIXTURES_DIR / f"{slug}{suffix}"
        if self.update or not fixture.exists():
            fixture.write_text(actual, encoding="utf-8")
            return
        expected = fixture.read_text(encoding="utf-8")
        if expected != actual:
            self.fail(
                f"{fixture.name} drifted from fixture. "
                f"Re-run with UPDATE_SNAPSHOTS=1 if intentional.\n\n"
                f"{_diff(expected, actual, fixture.name)}"
            )

    def test_html_snapshots(self):
        for slug in SNAPSHOT_RECIPES:
            with self.subTest(slug=slug):
                recipe = self.recipes_by_slug.get(slug)
                self.assertIsNotNone(recipe, f"recipe {slug} not found")
                ingredients_html, instructions_html = self.site.parse_recipe_content(recipe)
                rendered = f"INGREDIENTS:\n{ingredients_html}\n\nINSTRUCTIONS:\n{instructions_html}\n"
                self._check(slug, ".html.txt", rendered)

    def test_latex_snapshots(self):
        for slug in SNAPSHOT_RECIPES:
            with self.subTest(slug=slug):
                recipe = self.recipes_by_slug.get(slug)
                self.assertIsNotNone(recipe, f"recipe {slug} not found")
                rendered = self.pdf.format_recipe_latex(recipe) + "\n"
                self._check(slug, ".tex.txt", rendered)


if __name__ == "__main__":
    unittest.main()
