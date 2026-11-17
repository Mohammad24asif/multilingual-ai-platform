"""Interface every translation engine implements, plus shared parameter types."""

from __future__ import annotations

from collections.abc import Sequence
from dataclasses import dataclass
from typing import Protocol

from ...domain.models import ModelSpec


@dataclass(frozen=True, slots=True)
class GenerationParams:
    num_beams: int = 4
    max_new_tokens: int = 256
    length_penalty: float = 1.0

    def __post_init__(self) -> None:
        if not 1 <= self.num_beams <= 8:
            raise ValueError("num_beams must be between 1 and 8")
        if not 8 <= self.max_new_tokens <= 1024:
            raise ValueError("max_new_tokens must be between 8 and 1024")


@dataclass(frozen=True, slots=True)
class BackendContext:
    device: str  # "cpu" | "cuda"
    allow_download: bool = False  # False => local files only; the user downloads models explicitly
    torch_threads: int | None = None


class TranslationBackend(Protocol):
    spec: ModelSpec
    device: str
    supports_token_count: bool

    def load(self) -> None: ...

    def unload(self) -> None: ...

    def count_tokens(self, text: str, src_code: str) -> int: ...

    def translate_batch(
        self, texts: Sequence[str], src_code: str, tgt_code: str, params: GenerationParams
    ) -> list[str]: ...
