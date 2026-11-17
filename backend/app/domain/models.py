"""Plain data types describing languages and models. No framework imports, easy to test."""

from __future__ import annotations

import math
import re
from collections.abc import Mapping
from dataclasses import dataclass, field
from enum import StrEnum
from typing import Any

_SHA = re.compile(r"^[0-9a-f]{40}$")


class LicenceClass(StrEnum):
    PERMISSIVE = "permissive"  # e.g. MIT, Apache-2.0, CC-BY-4.0
    NON_COMMERCIAL = "non_commercial"  # e.g. CC-BY-NC-4.0 (research only)
    RESTRICTED = "restricted"  # custom terms with use restrictions
    UNKNOWN = "unknown"


@dataclass(frozen=True, slots=True)
class Licence:
    spdx: str
    klass: LicenceClass
    verified: bool = False  # True once confirmed against Hub metadata by scripts/pin_models.py (or reviewed by hand)
    note: str = ""


@dataclass(frozen=True, slots=True)
class Language:
    code: str  # canonical platform code (ISO 639-1 where one exists)
    name: str
    native_name: str
    scripts: tuple[str, ...]
    rtl: bool = False


@dataclass(frozen=True, slots=True)
class UnlistedLanguage:
    """A language we know shares a script with a listed one but have not added to the registry."""

    code: str
    name: str
    scripts: tuple[str, ...]


@dataclass(frozen=True, slots=True)
class ScriptInfo:
    name: str
    open: bool  # True when the script is used by an open-ended set of languages (Latin, Arabic, ...)
    note: str = ""


@dataclass(frozen=True, slots=True, eq=False)
class ModelSpec:
    id: str
    display_name: str
    family: str  # selects the backend implementation: "nllb" | "mbart50" | "indictrans2"
    task: str
    hf_repo: str
    revision: str | None
    licence: Licence
    requires_remote_code: bool
    params_millions: float | None
    language_codes: Mapping[str, str]  # platform code -> model-specific code
    sources: frozenset[str]
    targets: frozenset[str]
    priority: int
    enabled_by_default: bool
    segment_token_limit: int
    evidence: Mapping[str, Any] = field(default_factory=dict)
    notes: str = ""

    def supports(self, src: str, tgt: str) -> bool:
        return src != tgt and src in self.sources and tgt in self.targets

    def model_code(self, language: str) -> str:
        try:
            return self.language_codes[language]
        except KeyError as exc:
            raise KeyError(f"{self.id} has no code for language {language!r}") from exc

    @property
    def revision_pinned(self) -> bool:
        return bool(self.revision and _SHA.match(self.revision))

    @property
    def estimated_ram_mb(self) -> int | None:
        """Rough RAM need: float32 weights (4 bytes/parameter) plus 25% working overhead.

        This is an ESTIMATE from the declared parameter count, not a measurement.
        """
        if self.params_millions is None:
            return None
        return math.ceil(self.params_millions * 4 * 1.25)
