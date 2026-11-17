"""Request/result data types for the translation pipeline (plain dataclasses, framework-free)."""

from __future__ import annotations

from dataclasses import dataclass, field

from ..detection.detector import DetectionResult
from .backends.base import GenerationParams


@dataclass(frozen=True, slots=True)
class TranslationRequest:
    text: str
    target: str
    source: str = "auto"  # a registry language code, or "auto"
    model_id: str | None = None  # force one model (never substituted if it cannot serve the pair)
    allow_pivot: bool = False  # explicit consent to a two-step translation through English
    generation: GenerationParams | None = None


@dataclass(frozen=True, slots=True)
class TranslationConfig:
    max_chars: int = 20_000
    max_segments: int = 400
    max_batch_size: int = 8
    max_batch_tokens: int = 1_600
    job_timeout_s: float = 120.0
    min_target_script_share: float = 0.5
    default_generation: GenerationParams = field(default_factory=GenerationParams)


@dataclass(frozen=True, slots=True)
class ResultWarning:
    code: str
    detail: str
    count: int = 1


@dataclass(frozen=True, slots=True)
class LegResult:
    source: str
    target: str
    model_id: str
    model_revision: str | None
    licence: str
    device: str
    units: int
    batches: int
    split_units: dict[str, int]
    token_counts: str  # "tokenizer" (exact) or "estimate"
    queue_wait_s: float
    load_s: float
    inference_s: float


@dataclass(frozen=True, slots=True)
class TranslationResult:
    translation: str
    source_language: str
    source_detection: DetectionResult | None
    target_language: str
    legs: tuple[LegResult, ...]
    pivot_via: str | None
    segments: int
    input_chars: int
    output_chars: int
    warnings: tuple[ResultWarning, ...]
    timings_ms: dict[str, float]
    normalization: dict[str, int]
