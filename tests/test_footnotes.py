"""Unit tests for `footnotes.extract` and `footnotes.tokenize_inline`.

Snapshot tests cover end-to-end rendering of footnote markers; these pin the
extraction and tokenization layers in isolation.
"""

import unittest

from footnotes import Footnote, extract, tokenize_inline
from recipe_parser import Callout


def _bare(text: str) -> Callout:
    return Callout(kind="note", text=text, labeled=False)


class ExtractFootnotes(unittest.TestCase):
    def test_separates_def_paragraph_from_prose(self):
        callout = _bare("Vic invented it in 1944.[^1]\n\n[^1]: Bergeron, *Bartender's Guide*.")
        result = extract([callout])
        self.assertEqual(len(result.cleaned), 1)
        self.assertEqual(result.cleaned[0].text, "Vic invented it in 1944.[^1]")
        self.assertEqual(result.footnotes, [Footnote(num=1, text="Bergeron, *Bartender's Guide*.")])
        self.assertEqual(result.referenced, {1})

    def test_def_only_callout_yields_none_in_cleaned(self):
        # Trailing footnote-defs callout: cleaned slot is None so callers can
        # skip rendering, while position alignment with the input is preserved.
        callout = _bare("[^1]: Source A.\n\n[^2]: Source B.")
        result = extract([callout])
        self.assertEqual(result.cleaned, [None])
        self.assertEqual([f.num for f in result.footnotes], [1, 2])
        self.assertEqual(result.referenced, set())

    def test_cleaned_is_aligned_to_input(self):
        callouts = [
            _bare("First[^1]."),
            _bare("[^1]: A.\n\n[^2]: B."),
            _bare("Second[^2]."),
        ]
        result = extract(callouts)
        self.assertEqual(len(result.cleaned), 3)
        self.assertEqual(result.cleaned[0].text, "First[^1].")
        self.assertIsNone(result.cleaned[1])
        self.assertEqual(result.cleaned[2].text, "Second[^2].")
        self.assertEqual(result.referenced, {1, 2})

    def test_orders_footnotes_numerically(self):
        callout = _bare("[^3]: C.\n\n[^1]: A.\n\n[^2]: B.")
        result = extract([callout])
        self.assertEqual([f.num for f in result.footnotes], [1, 2, 3])

    def test_def_with_multiline_body(self):
        callout = _bare("[^1]: Line one\nstill line one.")
        result = extract([callout])
        self.assertEqual(result.footnotes, [Footnote(num=1, text="Line one\nstill line one.")])

    def test_last_def_wins_on_duplicate_number(self):
        callout = _bare("[^1]: First.\n\n[^1]: Second.")
        result = extract([callout])
        self.assertEqual(result.footnotes, [Footnote(num=1, text="Second.")])

    def test_preserves_callout_kind_and_labeled_flag(self):
        callout = Callout(kind="tip", text="Use[^1].\n\n[^1]: Source.", labeled=True)
        result = extract([callout])
        self.assertEqual(result.cleaned[0].kind, "tip")
        self.assertTrue(result.cleaned[0].labeled)

    def test_no_footnotes_is_passthrough(self):
        callout = _bare("Plain headnote with no footnotes.")
        result = extract([callout])
        self.assertEqual(result.cleaned, [callout])
        self.assertEqual(result.footnotes, [])
        self.assertEqual(result.referenced, set())


class TokenizeInline(unittest.TestCase):
    def test_plain_text_yields_single_text_token(self):
        self.assertEqual(list(tokenize_inline("just prose")), [("text", "just prose")])

    def test_footnote_ref_payload_is_int(self):
        # Pin int-not-str so renderers can use the payload directly without
        # parsing.
        self.assertEqual(list(tokenize_inline("a[^7]b")), [("text", "a"), ("ref", 7), ("text", "b")])

    def test_italic_payload_is_inner_text(self):
        self.assertEqual(
            list(tokenize_inline("read *Sippin' Safari* now")),
            [("text", "read "), ("italic", "Sippin' Safari"), ("text", " now")],
        )

    def test_mixed_markers(self):
        tokens = list(tokenize_inline("see *Berry*[^1] for more"))
        self.assertEqual(
            tokens,
            [("text", "see "), ("italic", "Berry"), ("ref", 1), ("text", " for more")],
        )

    def test_empty_string(self):
        self.assertEqual(list(tokenize_inline("")), [])


if __name__ == "__main__":
    unittest.main()
