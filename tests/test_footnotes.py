"""Unit tests for `footnotes.extract`.

End-to-end rendering of footnote markers (HTML superscripts, LaTeX
`\textsuperscript`) is covered by the snapshot tests on the Mai Tai recipe;
these tests pin the extraction layer in isolation.
"""

import unittest

from footnotes import Footnote, extract
from recipe_parser import Callout


def _bare(text: str) -> Callout:
    return Callout(kind="note", text=text, labeled=False)


class ExtractFootnotes(unittest.TestCase):
    def test_separates_def_paragraph_from_prose(self):
        callout = _bare("Vic invented it in 1944.[^1]\n\n[^1]: Bergeron, *Bartender's Guide*.")
        cleaned, footnotes, referenced = extract([callout])
        self.assertEqual(len(cleaned), 1)
        self.assertEqual(cleaned[0].text, "Vic invented it in 1944.[^1]")
        self.assertEqual(footnotes, [Footnote(num=1, text="Bergeron, *Bartender's Guide*.")])
        self.assertEqual(referenced, {1})

    def test_drops_callout_consisting_only_of_defs(self):
        # The trailing footnote-defs callout in Mai Tai is its own block — once
        # the defs are pulled out, no callout should remain.
        callout = _bare("[^1]: Source A.\n\n[^2]: Source B.")
        cleaned, footnotes, referenced = extract([callout])
        self.assertEqual(cleaned, [])
        self.assertEqual([f.num for f in footnotes], [1, 2])
        self.assertEqual(referenced, set())  # `[^1]` inside a def doesn't count

    def test_collects_refs_across_callouts_skipping_defs(self):
        callouts = [
            _bare("First[^1] and second[^2]."),
            _bare("Third[^3]."),
            _bare("[^1]: A.\n\n[^2]: B.\n\n[^3]: C."),
        ]
        cleaned, footnotes, referenced = extract(callouts)
        self.assertEqual(referenced, {1, 2, 3})
        self.assertEqual([f.num for f in footnotes], [1, 2, 3])
        # The defs-only callout is dropped; the prose callouts are kept verbatim.
        self.assertEqual(len(cleaned), 2)
        self.assertEqual(cleaned[0].text, "First[^1] and second[^2].")

    def test_orders_footnotes_numerically(self):
        callout = _bare("[^3]: C.\n\n[^1]: A.\n\n[^2]: B.")
        _, footnotes, _ = extract([callout])
        self.assertEqual([f.num for f in footnotes], [1, 2, 3])

    def test_def_with_multiline_body(self):
        # Once a paragraph starts with `[^N]:`, the rest of the paragraph is the
        # def body — including embedded newlines (rare, but the regex uses
        # DOTALL so it doesn't choke on them).
        callout = _bare("[^1]: Line one\nstill line one.")
        _, footnotes, _ = extract([callout])
        self.assertEqual(footnotes, [Footnote(num=1, text="Line one\nstill line one.")])

    def test_last_def_wins_on_duplicate_number(self):
        callout = _bare("[^1]: First.\n\n[^1]: Second.")
        _, footnotes, _ = extract([callout])
        self.assertEqual(footnotes, [Footnote(num=1, text="Second.")])

    def test_preserves_callout_kind_and_labeled_flag(self):
        callout = Callout(kind="tip", text="Use[^1].\n\n[^1]: Source.", labeled=True)
        cleaned, _, _ = extract([callout])
        self.assertEqual(cleaned[0].kind, "tip")
        self.assertTrue(cleaned[0].labeled)

    def test_no_footnotes_is_passthrough(self):
        callout = _bare("Plain headnote with no footnotes.")
        cleaned, footnotes, referenced = extract([callout])
        self.assertEqual(cleaned, [callout])
        self.assertEqual(footnotes, [])
        self.assertEqual(referenced, set())


if __name__ == "__main__":
    unittest.main()
