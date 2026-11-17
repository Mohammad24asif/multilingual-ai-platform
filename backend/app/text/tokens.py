"""Cheap token-count estimate used for planning before a model tokenizer is available.

This is an ESTIMATE (characters per token differs by script and tokenizer). Backends that own a real
tokenizer expose exact counts, which the translation service prefers.
"""

from __future__ import annotations

import math

from .scripts import profile_text

_CHARS_PER_TOKEN_LATIN = 4.0
_CHARS_PER_TOKEN_OTHER = 2.0


def estimate_tokens(text: str) -> int:
    if not text:
        return 0
    profile = profile_text(text)
    cpt = _CHARS_PER_TOKEN_LATIN if profile.dominant in (None, "Latin") else _CHARS_PER_TOKEN_OTHER
    return max(1, math.ceil(len(text) / cpt))
