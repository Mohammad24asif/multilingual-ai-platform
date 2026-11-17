"""Turn sentences into model-sized units and batches, and put the results back together.

Neural MT models are trained on sentence-sized inputs and have hard length limits. We therefore
1. split any sentence longer than ``max_tokens`` at clause punctuation, then at spaces, then (last resort)
   at characters - every split is recorded so it can be disclosed to the user;
2. group units into batches limited by size and token budget, sorted by length to reduce padding;
3. merge unit translations back into one string per original sentence.
Nothing is ever dropped: every unit index appears in exactly one batch.
"""

from __future__ import annotations

import re
from collections.abc import Callable, Sequence
from dataclasses import dataclass

TokenCounter = Callable[[str], int]

_CLAUSE_SPLIT = re.compile(r"(?<=[,;:،؛—–])(\s+)")
_WORD_SPLIT_NO_CAPTURE = re.compile(r"(?<=\S)(\s+)(?=\S)")


@dataclass(frozen=True, slots=True)
class Unit:
    seg_index: int
    text: str
    joiner: str  # whitespace that followed this unit inside its sentence ("" for the last unit)
    split: str | None  # None, "clause", "words" or "chars"


def _split_keeping_separators(text: str, pattern: re.Pattern[str]) -> list[tuple[str, str]]:
    parts = pattern.split(text)
    pieces: list[tuple[str, str]] = []
    for k in range(0, len(parts), 2):
        piece = parts[k]
        sep = parts[k + 1] if k + 1 < len(parts) else ""
        if piece:
            pieces.append((piece, sep))
    return pieces


def _pack(pieces: list[tuple[str, str]], count: TokenCounter, max_tokens: int) -> list[tuple[str, str]]:
    """Greedily join adjacent pieces while they fit; returns (text, joiner-after) pairs."""
    packed: list[tuple[str, str]] = []
    cur_text = ""
    cur_sep = ""
    for piece, sep in pieces:
        if not cur_text:
            cur_text, cur_sep = piece, sep
            continue
        candidate = cur_text + cur_sep + piece
        if count(candidate) <= max_tokens:
            cur_text, cur_sep = candidate, sep
        else:
            packed.append((cur_text, cur_sep))
            cur_text, cur_sep = piece, sep
    if cur_text:
        packed.append((cur_text, cur_sep))
    return packed


def _split_long(text: str, count: TokenCounter, max_tokens: int) -> list[tuple[str, str, str]]:
    """Return (text, joiner, split_kind) triples covering ``text``."""
    clause = _pack(_split_keeping_separators(text, _CLAUSE_SPLIT), count, max_tokens)
    result: list[tuple[str, str, str]] = []
    for piece, sep in clause:
        if count(piece) <= max_tokens:
            result.append((piece, sep, "clause"))
            continue
        words = _pack(_split_keeping_separators(piece, _WORD_SPLIT_NO_CAPTURE), count, max_tokens)
        for w_text, w_sep in words:
            if count(w_text) <= max_tokens:
                result.append((w_text, w_sep, "words"))
                continue
            size = max(1, int(len(w_text) * max_tokens / max(1, count(w_text))))
            for k in range(0, len(w_text), size):
                result.append((w_text[k : k + size], "", "chars"))
        # restore the separator that followed the clause piece after its last sub-unit
        last_text, _last_sep, last_kind = result[-1]
        result[-1] = (last_text, sep, last_kind)
    return result


def plan_units(segments: Sequence[str], *, count_tokens: TokenCounter, max_tokens: int) -> list[Unit]:
    if max_tokens < 1:
        raise ValueError("max_tokens must be >= 1")
    units: list[Unit] = []
    for idx, text in enumerate(segments):
        if count_tokens(text) <= max_tokens:
            units.append(Unit(idx, text, "", None))
            continue
        triples = _split_long(text, count_tokens, max_tokens)
        for pos, (piece, joiner, kind) in enumerate(triples):
            last = pos == len(triples) - 1
            units.append(Unit(idx, piece, "" if last else joiner, kind))
    return units


def merge_units(units: Sequence[Unit], translations: Sequence[str], n_segments: int) -> list[str]:
    """Join unit translations back into one string per original segment."""
    if len(units) != len(translations):
        raise ValueError("translation count must equal unit count")
    out = [""] * n_segments
    for unit, translated in zip(units, translations, strict=True):
        glue = " " if unit.split == "chars" else unit.joiner
        out[unit.seg_index] += translated + glue
    # units end with joiner == "" for the last piece of every segment, so no trailing glue remains
    return out


def plan_batches(
    units: Sequence[Unit], *, count_tokens: TokenCounter, max_batch_size: int, max_batch_tokens: int
) -> list[list[int]]:
    if max_batch_size < 1 or max_batch_tokens < 1:
        raise ValueError("batch limits must be >= 1")
    order = sorted(range(len(units)), key=lambda i: (count_tokens(units[i].text), i))
    batches: list[list[int]] = []
    current: list[int] = []
    current_max = 0
    for idx in order:
        tokens = count_tokens(units[idx].text)
        new_max = max(current_max, tokens)
        # padded cost of a batch is (items x longest item)
        if current and (len(current) + 1 > max_batch_size or new_max * (len(current) + 1) > max_batch_tokens):
            batches.append(current)
            current, current_max = [], 0
            new_max = tokens
        current.append(idx)
        current_max = new_max
    if current:
        batches.append(current)
    return batches
