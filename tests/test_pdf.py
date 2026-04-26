"""Unit tests for pdf_generator helpers."""

import unittest

from pdf_generator import PDFGenerator


class EscapeLatex(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.pdf = PDFGenerator()

    def test_empty(self):
        self.assertEqual(self.pdf.escape_latex(""), "")

    def test_ampersand_alone(self):
        self.assertEqual(self.pdf.escape_latex("Wray & Nephew"), r"Wray \& Nephew")

    def test_backslash_alone(self):
        self.assertEqual(self.pdf.escape_latex(r"a\b"), r"a\textbackslash{}b")

    def test_single_pass_does_not_re_escape_inserted_backslashes(self):
        # Sequential replacement would turn `&` -> `\&` then `\` -> `\textbackslash{}`,
        # producing `\textbackslash{}&`. Single-pass keeps it as `\&`.
        self.assertEqual(self.pdf.escape_latex("A & B"), r"A \& B")

    def test_braces_and_pct(self):
        self.assertEqual(self.pdf.escape_latex("50% off {sale}"), r"50\% off \{sale\}")

    def test_underscore_and_hash(self):
        self.assertEqual(self.pdf.escape_latex("foo_bar #1"), r"foo\_bar \#1")

    def test_tilde_and_caret(self):
        self.assertEqual(self.pdf.escape_latex("~/path^"), r"\textasciitilde{}/path\^{}")

    def test_passes_through_normal_text(self):
        self.assertEqual(self.pdf.escape_latex("hello, world."), "hello, world.")


if __name__ == "__main__":
    unittest.main()
