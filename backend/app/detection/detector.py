"""Script-based language detection that abstains instead of guessing.

What it can do honestly (no model, no invented confidence):
* find which writing systems a text uses and how much of each;
* resolve the language when the script belongs to exactly one known language (Telugu, Tamil, ...);
* resolve English for Latin text only when there is strong evidence (several English function words and
  no romanised-Indic markers);
* otherwise return ``ambiguous`` with the candidate list so the caller can ask the user.

A machine-learned identifier (chosen by measured accuracy on a labelled set) is planned for Milestone 2;
it plugs in behind the same ``detect`` interface.
"""

from __future__ import annotations

import re
from dataclasses import dataclass

from ..domain.registry import Registry
from ..text.scripts import profile_text

MIN_LETTERS = 3
DOMINANT_SHARE = 0.6

_ENGLISH_WORDS = frozenset(
    "the and of that with this from have was were which would there their been will your what about into "
    "because could should these those they them than then when where while does did not you we is are to in".split()
)
_ROMANISED_INDIC_MARKERS = frozenset(
    "hai hain hoon nahi nahin aur woh yeh kya mein raha rahi tha thi bhi hum tum aap kal ghar "
    "undi ledu enti nenu meeru naku andi chala ela vachindi".split()
)
_URDU_LETTERS = frozenset("ٹڈڑںے")
_WORD = re.compile(r"[A-Za-z']+")


@dataclass(frozen=True, slots=True)
class DetectionResult:
    status: str  # "resolved" | "ambiguous" | "unsupported_language" | "insufficient_text"
    language: str | None  # set when resolved or unsupported_language
    candidates: tuple[str, ...]  # registry language codes that remain possible
    unlisted_candidates: tuple[str, ...]  # names of known languages not in the registry that share the script
    script: str | None
    script_share: float  # observed fraction of letters in the dominant script - NOT a confidence score
    scripts: tuple[tuple[str, float], ...]
    method: str | None  # "unique_script" | "english_function_words" | None
    suggested: str | None = None  # a pre-selection for a confirm prompt, never auto-applied
    notes: tuple[str, ...] = ()


class LanguageDetector:
    def __init__(self, registry: Registry) -> None:
        self._registry = registry

    def detect(self, text: str) -> DetectionResult:
        profile = profile_text(text)
        ranked = tuple((name, round(share, 4)) for name, share in profile.ranked)
        if profile.total < MIN_LETTERS:
            return DetectionResult("insufficient_text", None, (), (), None, 0.0, ranked, None, notes=("too_few_letters",))
        script, share = profile.dominant, profile.dominant_share
        assert script is not None
        if share < DOMINANT_SHARE:
            names = [name for name, _ in profile.ranked[:2]]
            listed, unlisted = self._candidates_for(names)
            return DetectionResult("ambiguous", None, listed, unlisted, script, share, ranked, None, notes=("mixed_scripts",))

        known = self._registry.languages_for_script(script)
        listed = tuple(code for code, _name, is_listed in known if is_listed)
        unlisted = tuple(name for _code, name, is_listed in known if not is_listed)
        notes: list[str] = []
        script_note = self._registry.script_note(script)
        if script_note:
            notes.append(script_note)

        if not self._registry.script_is_open(script) and len(known) == 1:
            code, _name, is_listed = known[0]
            status = "resolved" if is_listed else "unsupported_language"
            return DetectionResult(status, code, listed, unlisted, script, share, ranked, "unique_script", notes=tuple(notes))

        if script == "Latin":
            if self._looks_english(text):
                return DetectionResult("resolved", "en", listed, unlisted, script, share, ranked, "english_function_words", notes=tuple(notes))
            notes.append("latin_text_without_strong_english_evidence")
            return DetectionResult("ambiguous", None, listed, unlisted, script, share, ranked, None, suggested="en" if "en" in listed else None, notes=tuple(notes))

        suggested = None
        if script == "Arabic" and any(ch in _URDU_LETTERS for ch in text) and "ur" in listed:
            suggested = "ur"
            notes.append("urdu_specific_letters_present_but_not_decisive")
        return DetectionResult("ambiguous", None, listed, unlisted, script, share, ranked, None, suggested=suggested, notes=tuple(notes))

    def _candidates_for(self, scripts: list[str]) -> tuple[tuple[str, ...], tuple[str, ...]]:
        listed: list[str] = []
        unlisted: list[str] = []
        for script in scripts:
            for code, name, is_listed in self._registry.languages_for_script(script):
                if is_listed and code not in listed:
                    listed.append(code)
                elif not is_listed and name not in unlisted:
                    unlisted.append(name)
        return tuple(listed), tuple(unlisted)

    @staticmethod
    def _looks_english(text: str) -> bool:
        words = [w.lower().strip("'") for w in _WORD.findall(text)]
        if len(words) < 5:
            return False
        if len({w for w in words if w in _ROMANISED_INDIC_MARKERS}) >= 2:
            return False
        hits = [w for w in words if w in _ENGLISH_WORDS]
        return len(set(hits)) >= 3 and len(hits) / len(words) >= 0.25
