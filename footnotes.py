"""Footnote extraction and inline-marker tokenization for callout text.

Authors mark up Markdown-style footnotes inside `>` callouts:

    > Vic claimed he invented the drink in 1944.[^1]
    > [^1]: Bergeron, *Trader Vic's Bartender's Guide* (1972).

`extract` separates `[^N]: ...` definition paragraphs from prose paragraphs
in a single pass, returning the cleaned callouts (parallel to input, with
None where a callout was entirely defs), the sorted definitions, and the
set of inline-referenced numbers. `tokenize_inline` walks prose text and
yields typed segments so HTML and LaTeX renderers share one parser.
"""

import re
from collections.abc import Iterator
from dataclasses import dataclass, replace
from typing import Literal

from recipe_parser import Callout

FOOTNOTE_REF_RE = re.compile(r"\[\^(\d+)\]")
FOOTNOTE_DEF_RE = re.compile(r"^\[\^(\d+)\]:\s*(.+)$", re.DOTALL)

# Captures the payload directly so callers don't slice off the markers.
_INLINE_TOKEN_RE = re.compile(r"\[\^(?P<ref>\d+)\]|\*(?P<italic>[^*\n]+?)\*")


@dataclass(frozen=True)
class Footnote:
    num: int
    text: str


@dataclass(frozen=True)
class ExtractResult:
    # Parallel to the input list; None where every paragraph was a footnote def.
    cleaned: list[Callout | None]
    footnotes: list[Footnote]
    referenced: set[int]


InlineToken = tuple[Literal["text", "ref", "italic"], str | int]


def extract(callouts: list[Callout]) -> ExtractResult:
    """Pull `[^N]: ...` paragraphs out of each callout's text.

    Last def wins on duplicate N. References are collected from non-def
    paragraphs only, so a def's own `[^N]:` token does not count as a use.
    """
    cleaned: list[Callout | None] = []
    defs: dict[int, str] = {}
    referenced: set[int] = set()
    for callout in callouts:
        kept: list[str] = []
        for paragraph in callout.text.split("\n\n"):
            match = FOOTNOTE_DEF_RE.match(paragraph.strip())
            if match:
                defs[int(match.group(1))] = match.group(2).strip()
            else:
                kept.append(paragraph)
                referenced.update(int(m.group(1)) for m in FOOTNOTE_REF_RE.finditer(paragraph))
        cleaned.append(replace(callout, text="\n\n".join(kept)) if kept else None)
    footnotes = [Footnote(num=n, text=t) for n, t in sorted(defs.items())]
    return ExtractResult(cleaned=cleaned, footnotes=footnotes, referenced=referenced)


def tokenize_inline(text: str) -> Iterator[InlineToken]:
    """Yield `("text", str)`, `("ref", int)`, and `("italic", str)` segments."""
    cursor = 0
    for match in _INLINE_TOKEN_RE.finditer(text):
        if match.start() > cursor:
            yield "text", text[cursor : match.start()]
        if (ref := match.group("ref")) is not None:
            yield "ref", int(ref)
        else:
            yield "italic", match.group("italic")
        cursor = match.end()
    if cursor < len(text):
        yield "text", text[cursor:]
