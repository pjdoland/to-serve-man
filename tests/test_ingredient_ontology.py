"""Tests for the ingredient ontology — canonicalization + load-time validation.

The lookup-shape tests use the real ingredients.yaml so they break if a
real-world canonical id ever changes silently. The validation tests stub
the file via reset_cache + monkeypatched config.PROJECT_ROOT to assert
that bad ontology data fails loud at import time.
"""

import tempfile
import unittest
import unittest.mock
from pathlib import Path

import config
import ingredient_ontology as iov
from ingredient_ontology import canonical_ingredient, category_of


class CanonicalIngredient(unittest.TestCase):
    def test_alias_collapses_to_id(self):
        self.assertEqual(canonical_ingredient("fresh lime juice"), "lime-juice")
        self.assertEqual(canonical_ingredient("lime juice"), "lime-juice")

    def test_case_and_whitespace_insensitive(self):
        self.assertEqual(canonical_ingredient("LIME JUICE"), "lime-juice")
        self.assertEqual(canonical_ingredient("  Lime Juice  "), "lime-juice")

    def test_diacritic_alias(self):
        self.assertEqual(canonical_ingredient("orange curaçao"), "orange-curacao")
        self.assertEqual(canonical_ingredient("orange curacao"), "orange-curacao")

    def test_unmatched_returns_none(self):
        # Ingredients not in the ontology fall through — callers preserve the
        # raw display string in that case.
        self.assertIsNone(canonical_ingredient("Smith & Cross"))
        self.assertIsNone(canonical_ingredient("Mariano's Mix No. 7"))

    def test_empty_returns_none(self):
        self.assertIsNone(canonical_ingredient(""))
        self.assertIsNone(canonical_ingredient(None))

    def test_category_lookup(self):
        self.assertEqual(category_of("lime-juice"), "juice")
        self.assertEqual(category_of("angostura-bitters"), "bitters")
        self.assertEqual(category_of("aged-pot-still-jamaican-rum"), "spirit")
        self.assertIsNone(category_of("not-a-real-id"))


class OntologyValidation(unittest.TestCase):
    """Bad ontology data must fail loud at load time, not silently mis-bucket."""

    def _run_with_yaml(self, yaml_text: str):
        with tempfile.TemporaryDirectory() as tmp:
            (Path(tmp) / "ingredients.yaml").write_text(yaml_text, encoding="utf-8")
            iov.reset_cache()
            with unittest.mock.patch.object(config, "PROJECT_ROOT", Path(tmp)):
                return iov._load()

    def tearDown(self):
        # Restore the real ontology so subsequent tests see production data.
        iov.reset_cache()

    def test_duplicate_alias_raises(self):
        with self.assertRaises(ValueError) as cm:
            self._run_with_yaml(
                "ingredients:\n"
                "  - { id: a, category: juice, aliases: [foo] }\n"
                "  - { id: b, category: spirit, aliases: [foo] }\n"
            )
        self.assertIn("foo", str(cm.exception))

    def test_unknown_category_raises(self):
        with self.assertRaises(ValueError) as cm:
            self._run_with_yaml("ingredients:\n  - { id: a, category: bogus, aliases: [foo] }\n")
        self.assertIn("bogus", str(cm.exception))

    def test_non_slug_id_raises(self):
        with self.assertRaises(ValueError) as cm:
            self._run_with_yaml("ingredients:\n  - { id: 'Not A Slug', category: juice, aliases: [foo] }\n")
        self.assertIn("Not A Slug", str(cm.exception))

    def test_missing_file_returns_empty_ontology(self):
        # Soft-fail: a project without ingredients.yaml builds successfully,
        # canonical_ingredient just returns None for everything.
        with tempfile.TemporaryDirectory() as tmp:
            iov.reset_cache()
            with unittest.mock.patch.object(config, "PROJECT_ROOT", Path(tmp)):
                ontology = iov._load()
                self.assertEqual(ontology.alias_to_id, {})
                self.assertEqual(ontology.id_to_category, {})


if __name__ == "__main__":
    unittest.main()
