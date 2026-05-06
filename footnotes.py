"""Footnote extraction and inline formatting for callout text.

Authors mark up Markdown-style footnotes inside `>` callouts:

    > Vic claimed he invented the drink in 1944.[^1]
    > [^1]: Bergeron, *Trader Vic's Bartender's Guide* (1972).

`extract` pulls definition paragraphs (`[^N]: ...`) out of the callout list
and returns them as a sorted list of `Footnote` objects, plus the set of
numbers actually referenced inline. Renderers turn `[^N]` into a superscript
link and emit a separate footnotes section at the bottom of the recipe.
"""

import re
from dataclasses import dataclass, replace

from recipe_parser import Callout

FOOTNOTE_REF_RE = re.compile(r"\[\^(\d+)\]")
FOOTNOTE_DEF_RE = re.compile(r"^\[\^(\d+)\]:\s*(.+)$", re.DOTALL)


@dataclass(frozen=True)
class Footnote:
    num: int
    text: str


def extract(callouts: list[Callout]) -> tuple[list[Callout], list[Footnote], set[int]]:
    """Split footnote defs out of callout text.

    A paragraph (split by `\\n\\n`) is a footnote definition iff its first
    non-whitespace characters match `[^N]:`. Mixed paragraphs (def + prose) are
    not split — keep one def per paragraph (the natural `> [^N]: ...` form).

    Last def wins on duplicate N. Refs are collected from non-def paragraphs
    only, so a def's own `[^N]` token does not count as a reference.
    """
    cleaned: list[Callout] = []
    defs: dict[int, str] = {}
    referenced: set[int] = set()
    for callout in callouts:
        kept_paragraphs: list[str] = []
        for paragraph in callout.text.split("\n\n"):
            stripped = paragraph.strip()
            match = FOOTNOTE_DEF_RE.match(stripped)
            if match:
                defs[int(match.group(1))] = match.group(2).strip()
            else:
                kept_paragraphs.append(paragraph)
                for ref in FOOTNOTE_REF_RE.finditer(paragraph):
                    referenced.add(int(ref.group(1)))
        if kept_paragraphs:
            cleaned.append(replace(callout, text="\n\n".join(kept_paragraphs)))
    footnotes = [Footnote(num=n, text=t) for n, t in sorted(defs.items())]
    return cleaned, footnotes, referenced
