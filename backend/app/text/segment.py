"""Sentence segmentation for English and Indian languages, designed to be lossless.

``SegmentedText.render`` puts translated sentences back using the *exact* whitespace that followed each
source sentence, so paragraph and line structure survive translation. With identity "translations" the
rendered text equals the input - that invariant is tested with fuzzing.

Rules (deliberately simple and documented; see docs/LIMITATIONS.md):
* A newline always ends a segment.
* ``? ! । ॥ ؟ ۔`` end a segment when followed by whitespace or end of text.
* ``.`` and ``…`` also end a segment, except: after a short abbreviation (Dr., Mr., e.g. ...), after a list
  marker such as ``1.`` at the start of a segment, a single initial (``A.``), or when the next
  non-space character is a lowercase Latin letter (``3.30 p.m. today``).
"""

from __future__ import annotations

import re
from collections.abc import Sequence
from dataclasses import dataclass

_TERMINATORS = frozenset(".?!…।॥؟۔")
_STRONG_TERMINATORS = frozenset("?!।॥؟۔")
_CLOSERS = frozenset("\"'”’»)]}›")
_OPENERS = frozenset("\"'“‘«([{‹")

DEFAULT_ABBREVIATIONS = frozenset(
    {"dr", "mr", "mrs", "ms", "prof", "sr", "jr", "st", "mt", "vs", "fig", "cf", "viz", "e.g", "i.e", "approx", "dept"}
)
_DOTTED_INITIALS = re.compile(r"^(?:[A-Za-z]\.)+[A-Za-z]$")
_LIST_MARKER = re.compile(r"^\(?\d{1,3}$")
_INITIAL = re.compile(r"^[A-Za-z]$")


@dataclass(frozen=True, slots=True)
class Segment:
    text: str  # the sentence, without surrounding whitespace
    sep: str  # exact whitespace that followed it in the source
    start: int
    end: int


@dataclass(frozen=True, slots=True)
class SegmentedText:
    lead: str
    segments: tuple[Segment, ...]

    def texts(self) -> list[str]:
        return [s.text for s in self.segments]

    def render(self, replacements: Sequence[str]) -> str:
        if len(replacements) != len(self.segments):
            raise ValueError("replacement count must equal segment count")
        parts = [self.lead]
        for seg, new_text in zip(self.segments, replacements, strict=True):
            parts.append(new_text)
            parts.append(seg.sep)
        return "".join(parts)


def _word_before(text: str, idx: int) -> str:
    j = idx
    while j > 0 and not text[j - 1].isspace() and text[j - 1] not in _OPENERS:
        j -= 1
    return text[j:idx]


def _next_non_space(text: str, idx: int) -> str:
    n = len(text)
    while idx < n and text[idx].isspace():
        idx += 1
    return text[idx] if idx < n else ""


def _is_boundary(text: str, seg_start: int, first: int, cluster_end: int, abbreviations: frozenset[str]) -> bool:
    """Decide whether the terminator cluster text[first:cluster_end] ends a sentence."""
    cluster = text[first:cluster_end]
    if any(c in _STRONG_TERMINATORS for c in cluster):
        return True
    # Only dots / ellipsis characters remain.
    word = _word_before(text, first)
    prefix = text[seg_start:first]
    if _LIST_MARKER.match(prefix) or _INITIAL.match(prefix):
        return False
    if word.lower().rstrip(".") in abbreviations:
        return False
    nxt = _next_non_space(text, cluster_end)
    if "a" <= nxt <= "z":
        return False
    if _DOTTED_INITIALS.match(word) and not ("A" <= nxt <= "Z"):
        return False
    return True


def segment_text(text: str, *, abbreviations: frozenset[str] = DEFAULT_ABBREVIATIONS) -> SegmentedText:
    n = len(text)
    i = 0
    while i < n and text[i].isspace():
        i += 1
    lead = text[:i]
    segments: list[Segment] = []
    seg_start = i

    def close(end: int) -> int:
        """Close the current segment at ``end`` and return the index after the following whitespace."""
        nonlocal seg_start
        k = end
        while k < n and text[k].isspace():
            k += 1
        segments.append(Segment(text=text[seg_start:end], sep=text[end:k], start=seg_start, end=end))
        seg_start = k
        return k

    while i < n:
        ch = text[i]
        if ch == "\n":
            end = i
            while end > seg_start and text[end - 1].isspace():
                end -= 1
            i = close(end)
            continue
        if ch in _TERMINATORS:
            j = i
            while j < n and text[j] in _TERMINATORS:
                j += 1
            cluster_end = j
            while j < n and text[j] in _CLOSERS:
                j += 1
            if (j == n or text[j].isspace()) and _is_boundary(text, seg_start, i, cluster_end, abbreviations):
                i = close(j)
            else:
                i = j
            continue
        i += 1

    if seg_start < n:
        end = n
        while end > seg_start and text[end - 1].isspace():
            end -= 1
        segments.append(Segment(text=text[seg_start:end], sep=text[end:], start=seg_start, end=end))
    return SegmentedText(lead=lead, segments=tuple(segments))
