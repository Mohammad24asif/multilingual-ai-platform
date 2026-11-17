"""Unicode and whitespace normalisation that never damages Indic or right-to-left text.

Design rules (see ADR-006):
* NFC only. NFKC rewrites characters in ways that can change meaning, so it is not used.
* ZWJ (U+200D) and ZWNJ (U+200C) are preserved: they decide how conjuncts and half-forms are drawn in
  Telugu, Hindi, Malayalam, Bengali and others. LRM/RLM are preserved for mixed-direction (Urdu) text.
* Invisible junk (BOM, soft hyphen, word joiner, other control characters) is removed.
* The original text is always kept next to the processed text.
"""

from __future__ import annotations

import re
import unicodedata
from dataclasses import dataclass, field

ZWJ = "\u200d"
ZWNJ = "\u200c"
LRM = "\u200e"
RLM = "\u200f"
_KEEP_FORMAT = frozenset({ZWJ, ZWNJ, LRM, RLM})
_TO_NEWLINE = frozenset({"\u0085", "\u2028", "\u2029", "\x0b", "\x0c"})

_SPACE_RUN = re.compile(r"[ \t]+")
_TRAILING_SPACE = re.compile(r" +\n")
_LEADING_SPACE = re.compile(r"\n +")


@dataclass(frozen=True, slots=True)
class NormalizedText:
    original: str
    text: str
    stats: dict[str, int] = field(default_factory=dict)

    @property
    def changed(self) -> bool:
        return self.original != self.text


def _clean_characters(text: str, stats: dict[str, int]) -> str:
    out: list[str] = []
    for ch in text:
        if ch == "\n" or ch == "\t":
            out.append(ch)
        elif ch in _TO_NEWLINE:
            out.append("\n")
            stats["newline_variants"] = stats.get("newline_variants", 0) + 1
        else:
            category = unicodedata.category(ch)
            if category == "Cc":
                stats["control_removed"] = stats.get("control_removed", 0) + 1
            elif category == "Cs":
                stats["surrogate_removed"] = stats.get("surrogate_removed", 0) + 1
            elif category == "Cf" and ch not in _KEEP_FORMAT:
                stats["format_removed"] = stats.get("format_removed", 0) + 1
            elif category == "Zs" and ch != " ":
                out.append(" ")
                stats["space_variants"] = stats.get("space_variants", 0) + 1
            else:
                out.append(ch)
    return "".join(out)


def normalize_text(text: str, *, collapse_spaces: bool = True, max_blank_lines: int = 1) -> NormalizedText:
    """Return a cleaned copy of ``text`` (see module docstring for the rules)."""
    stats: dict[str, int] = {}
    work = text.replace("\r\n", "\n").replace("\r", "\n")
    work = _clean_characters(work, stats)
    # NFC runs after removals so that removing an invisible character can never leave a pair
    # that would compose on a second pass (this keeps the function idempotent).
    work = unicodedata.normalize("NFC", work)
    if collapse_spaces:
        work = _SPACE_RUN.sub(" ", work)
        work = _TRAILING_SPACE.sub("\n", work)
        work = _LEADING_SPACE.sub("\n", work)
        limit = max_blank_lines + 1
        work = re.sub(r"\n{%d,}" % (limit + 1), "\n" * limit, work)
        work = work.strip(" \n")
    return NormalizedText(original=text, text=work, stats=stats)
