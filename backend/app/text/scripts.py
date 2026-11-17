"""Unicode script detection helpers (pure Python, no third-party dependencies).

Script recognition is NOT language identification. The Devanagari script is used by Hindi, Marathi,
Nepali, Sanskrit and others, so a script only tells us which languages are *possible*.
This module answers one narrow question: which writing systems appear in a text, and how much of each.
"""

from __future__ import annotations

import unicodedata
from bisect import bisect_right
from collections import Counter
from dataclasses import dataclass

# (first code point, last code point, script). Ranges must not overlap.
_RANGES: list[tuple[int, int, str]] = sorted(
    [
        (0x0041, 0x005A, "Latin"),
        (0x0061, 0x007A, "Latin"),
        (0x00AA, 0x00AA, "Latin"),
        (0x00BA, 0x00BA, "Latin"),
        (0x00C0, 0x00D6, "Latin"),
        (0x00D8, 0x00F6, "Latin"),
        (0x00F8, 0x02AF, "Latin"),
        (0x0370, 0x03FF, "Greek"),
        (0x0400, 0x052F, "Cyrillic"),
        (0x0590, 0x05FF, "Hebrew"),
        (0x0600, 0x06FF, "Arabic"),
        (0x0750, 0x077F, "Arabic"),
        (0x08A0, 0x08FF, "Arabic"),
        (0x0900, 0x097F, "Devanagari"),
        (0x0980, 0x09FF, "Bengali"),
        (0x0A00, 0x0A7F, "Gurmukhi"),
        (0x0A80, 0x0AFF, "Gujarati"),
        (0x0B00, 0x0B7F, "Oriya"),
        (0x0B80, 0x0BFF, "Tamil"),
        (0x0C00, 0x0C7F, "Telugu"),
        (0x0C80, 0x0CFF, "Kannada"),
        (0x0D00, 0x0D7F, "Malayalam"),
        (0x0D80, 0x0DFF, "Sinhala"),
        (0x0E00, 0x0E7F, "Thai"),
        (0x1100, 0x11FF, "Hangul"),
        (0x1C50, 0x1C7F, "OlChiki"),
        (0x1E00, 0x1EFF, "Latin"),
        (0x2C60, 0x2C7F, "Latin"),
        (0x3040, 0x30FF, "Japanese-Kana"),
        (0x3400, 0x4DBF, "Han"),
        (0x4E00, 0x9FFF, "Han"),
        (0xA720, 0xA7FF, "Latin"),
        (0xA8E0, 0xA8FF, "Devanagari"),
        (0xAAE0, 0xAAFF, "MeeteiMayek"),
        (0xABC0, 0xABFF, "MeeteiMayek"),
        (0xAC00, 0xD7AF, "Hangul"),
        (0xFB50, 0xFDFF, "Arabic"),
        (0xFE70, 0xFEFF, "Arabic"),
        (0xFF21, 0xFF3A, "Latin"),
        (0xFF41, 0xFF5A, "Latin"),
    ]
)
_STARTS = [r[0] for r in _RANGES]


def script_of(ch: str) -> str | None:
    """Return the script of a letter or combining mark, or None for digits, punctuation, spaces, etc."""
    if unicodedata.category(ch)[0] not in ("L", "M"):
        return None
    cp = ord(ch)
    idx = bisect_right(_STARTS, cp) - 1
    if idx >= 0:
        lo, hi, name = _RANGES[idx]
        if lo <= cp <= hi:
            return name
    return None


@dataclass(frozen=True, slots=True)
class ScriptProfile:
    """How much of each script a text contains. Shares are observed fractions, not confidence scores."""

    counts: dict[str, int]
    total: int

    @property
    def ranked(self) -> tuple[tuple[str, float], ...]:
        if self.total == 0:
            return ()
        pairs = sorted(self.counts.items(), key=lambda kv: (-kv[1], kv[0]))
        return tuple((name, count / self.total) for name, count in pairs)

    @property
    def dominant(self) -> str | None:
        ranked = self.ranked
        return ranked[0][0] if ranked else None

    @property
    def dominant_share(self) -> float:
        ranked = self.ranked
        return ranked[0][1] if ranked else 0.0

    def share(self, script: str) -> float:
        return self.counts.get(script, 0) / self.total if self.total else 0.0


def profile_text(text: str) -> ScriptProfile:
    """Count letters and combining marks per script. Digits, punctuation and spaces are ignored."""
    counter: Counter[str] = Counter()
    for ch in text:
        name = script_of(ch)
        if name is not None:
            counter[name] += 1
    return ScriptProfile(counts=dict(counter), total=sum(counter.values()))
