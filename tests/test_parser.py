"""Direct unit tests for `recipe_parser.parse_body`.

Snapshot tests cover end-to-end rendering for a few representative recipes;
these tests pin the parsing-layer contract for tokens, callouts, and sections
in isolation.
"""

import unittest

from recipe_parser import (
    Callout,
    Cookware,
    Ingredient,
    Section,
    Step,
    Text,
    Timer,
    parse_body,
)


def _blocks(body: str):
    return parse_body(body).blocks


class ParseBodyBlocks(unittest.TestCase):
    def test_section_header(self):
        [block] = _blocks(">> Mise en place")
        self.assertEqual(block, Section(name="Mise en place"))

    def test_kinded_callouts(self):
        body = "\n".join([">note Chill the glass.", ">tip Use a fine strainer.", ">warning Hot oil."])
        kinds = [(b.kind, b.text, b.labeled) for b in _blocks(body) if isinstance(b, Callout)]
        self.assertEqual(
            kinds,
            [
                ("note", "Chill the glass.", True),
                ("tip", "Use a fine strainer.", True),
                ("warning", "Hot oil.", True),
            ],
        )

    def test_bare_note_becomes_unlabeled_callout(self):
        [block] = _blocks("> A historical headnote about the drink.")
        self.assertEqual(
            block, Callout(kind="note", text="A historical headnote about the drink.", labeled=False)
        )

    def test_bare_note_does_not_swallow_section_or_kinded(self):
        # `>>` and `>note` must win over the bare-note fallback.
        body = "\n".join([">> Section", ">note labeled", "> bare"])
        blocks = _blocks(body)
        self.assertEqual(blocks[0], Section(name="Section"))
        self.assertEqual(blocks[1], Callout(kind="note", text="labeled", labeled=True))
        self.assertEqual(blocks[2], Callout(kind="note", text="bare", labeled=False))

    def test_comments_are_dropped(self):
        body = "\n".join(["-- a comment", "Stir gently."])
        blocks = _blocks(body)
        self.assertEqual(len(blocks), 1)
        self.assertIsInstance(blocks[0], Step)

    def test_consecutive_bare_notes_merge_with_paragraph_separator(self):
        # Two `> prose` lines separated by a `>` blockquote-paragraph marker
        # become ONE multi-paragraph callout (Markdown semantics), not two
        # adjacent asides. Paragraphs are joined with a "\n\n" sentinel that
        # the renderer expands into <p>...</p>.
        body = "\n".join(["> Headnote one.", ">", "> Headnote two."])
        blocks = _blocks(body)
        self.assertEqual(len(blocks), 1)
        self.assertEqual(
            blocks[0], Callout(kind="note", text="Headnote one.\n\nHeadnote two.", labeled=False)
        )

    def test_consecutive_bare_notes_merge_without_separator(self):
        # Two adjacent `> prose` lines (no `>` between them) also merge — the
        # only way to author distinct paragraphs in this scheme is one note
        # per line. Visual outcome: one aside with two paragraphs.
        body = "\n".join(["> Para 1.", "> Para 2."])
        blocks = _blocks(body)
        self.assertEqual(len(blocks), 1)
        self.assertEqual(blocks[0].text, "Para 1.\n\nPara 2.")

    def test_kinded_callout_breaks_bare_note_merge(self):
        # `>tip` between two bare notes resets the merge — bare note 2 starts
        # a fresh aside rather than appending to bare note 1.
        body = "\n".join(["> Bare 1.", ">tip Use ice.", "> Bare 2."])
        blocks = _blocks(body)
        self.assertEqual(len(blocks), 3)
        self.assertEqual(blocks[0].text, "Bare 1.")
        self.assertEqual(blocks[2].text, "Bare 2.")


class ParseBodyTokens(unittest.TestCase):
    def test_braced_ingredient_parses_qty_and_unit(self):
        parsed = parse_body("Add @sugar{2%tbsp}.")
        [step] = [b for b in parsed.blocks if isinstance(b, Step)]
        self.assertEqual(step.tokens[0], Text(text="Add "))
        self.assertEqual(step.tokens[1], Ingredient(name="sugar", qty="2", unit="tbsp"))
        self.assertEqual(step.tokens[2], Text(text="."))
        self.assertEqual(parsed.ingredients, [Ingredient(name="sugar", qty="2", unit="tbsp")])

    def test_bare_ingredient_token(self):
        parsed = parse_body("Garnish with @mint and serve.")
        [step] = parsed.blocks
        bare = [t for t in step.tokens if isinstance(t, Ingredient)]
        self.assertEqual(bare, [Ingredient(name="mint", from_braces=False)])
        # Bare-form ingredients are still added to the dedup list under the
        # current implementation; pin that behaviour so future changes are
        # intentional.
        self.assertEqual(len(parsed.ingredients), 1)

    def test_bare_ingredient_greedily_consumes_trailing_punctuation(self):
        # Known parser quirk: `@x.` parses as ingredient "x." because `.` is
        # not in the bare-ingredient terminator set. Recipes should brace-form
        # (`@mint{}`) or insert a space before punctuation if they care.
        parsed = parse_body("Garnish with @mint.")
        [step] = parsed.blocks
        bare = [t for t in step.tokens if isinstance(t, Ingredient)]
        self.assertEqual(bare, [Ingredient(name="mint.", from_braces=False)])

    def test_cookware_braced_and_bare(self):
        parsed = parse_body("In a #cocktail shaker{} combine; stir with a #spoon.")
        [step] = parsed.blocks
        cw = [t for t in step.tokens if isinstance(t, Cookware)]
        self.assertEqual(cw, [Cookware(name="cocktail shaker"), Cookware(name="spoon")])

    def test_timer(self):
        parsed = parse_body("Shake for ~{15%seconds}.")
        [step] = parsed.blocks
        timers = [t for t in step.tokens if isinstance(t, Timer)]
        self.assertEqual(timers, [Timer(value="15", unit="seconds")])

    def test_ingredient_dedup_preserves_first_appearance_order(self):
        body = "Add @rum{1%oz} and @lime{0.5%oz}. Then more @rum{1%oz}."
        parsed = parse_body(body)
        names = [i.name for i in parsed.ingredients]
        self.assertEqual(names, ["rum", "lime"])


class ParseBodyFrontmatter(unittest.TestCase):
    def test_frontmatter_is_stripped(self):
        body = "---\ntitle: Test\n---\nStir.\n"
        blocks = _blocks(body)
        self.assertEqual(len(blocks), 1)
        self.assertIsInstance(blocks[0], Step)


if __name__ == "__main__":
    unittest.main()
