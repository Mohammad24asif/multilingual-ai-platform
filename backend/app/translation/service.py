"""The translation pipeline: validate -> detect -> route -> segment -> translate -> validate -> report.

Everything that is not heavy inference runs on the event loop; the model work runs on the single
inference worker (see inference/executor.py). The result always says which model(s) produced it,
whether a pivot was used, how long each stage took and which sanity checks raised warnings.
It never contains an invented confidence number.
"""

from __future__ import annotations

import logging
import time
from collections import Counter
from collections.abc import Sequence
from dataclasses import dataclass

from ..core.errors import (
    InferenceError,
    InvalidInputError,
    LanguageAmbiguousError,
    OutputValidationError,
    PlatformError,
    UnsupportedLanguageError,
)
from ..core.logging import log_event
from ..detection.detector import DetectionResult, LanguageDetector
from ..domain.registry import Registry
from ..inference.executor import CancelToken, InferenceExecutor
from ..inference.manager import ModelManager
from ..text.chunk import merge_units, plan_batches, plan_units
from ..text.normalize import normalize_text
from ..text.scripts import profile_text
from ..text.segment import segment_text
from ..text.tokens import estimate_tokens
from .backends.base import GenerationParams
from .router import Route, RoutePlan, TranslationRouter
from .types import LegResult, ResultWarning, TranslationConfig, TranslationRequest, TranslationResult

logger = logging.getLogger(__name__)


@dataclass(slots=True)
class _LegOutput:
    texts: list[str]
    units: int
    batches: int
    split_units: dict[str, int]
    token_counts: str
    load_s: float
    inference_s: float
    device: str


def _ms(seconds: float) -> float:
    return round(seconds * 1000, 2)


class TranslationService:
    def __init__(
        self,
        *,
        registry: Registry,
        router: TranslationRouter,
        models: ModelManager,
        executor: InferenceExecutor,
        detector: LanguageDetector,
        config: TranslationConfig | None = None,
    ) -> None:
        self._registry = registry
        self._router = router
        self._models = models
        self._executor = executor
        self._detector = detector
        self._config = config or TranslationConfig()

    # -- public ------------------------------------------------------------------------------
    def explain_route(self, source: str, target: str, *, model_id: str | None = None, allow_pivot: bool = False) -> RoutePlan:
        """What would happen for this pair, without running a model."""
        return self._router.plan(source, target, model_id=model_id, allow_pivot=allow_pivot)

    async def translate(self, request: TranslationRequest) -> TranslationResult:
        cfg = self._config
        clock = time.perf_counter
        started = clock()
        timings: dict[str, float] = {}

        norm = normalize_text(request.text)
        timings["normalize_ms"] = _ms(clock() - started)
        if not norm.text:
            raise InvalidInputError("The text is empty after removing invisible characters and spaces.", code="empty_text")
        if len(norm.text) > cfg.max_chars:
            raise InvalidInputError(
                f"The text is longer than the limit of {cfg.max_chars} characters.",
                code="text_too_long",
                extra={"max_chars": cfg.max_chars, "chars": len(norm.text)},
            )
        if self._registry.language(request.target) is None:
            raise UnsupportedLanguageError(f"Target language '{request.target}' is not in the registry.", extra={"language": request.target})

        t = clock()
        detection: DetectionResult | None = None
        source = request.source
        if source == "auto":
            detection = self._detector.detect(norm.text)
            source = self._resolve_source(detection)
        elif self._registry.language(source) is None:
            raise UnsupportedLanguageError(f"Source language '{source}' is not in the registry.", extra={"language": source})
        timings["detect_ms"] = _ms(clock() - t)

        plan = self._router.plan(source, request.target, model_id=request.model_id, allow_pivot=request.allow_pivot)

        segmented = segment_text(norm.text)
        if len(segmented.segments) > cfg.max_segments:
            raise InvalidInputError(
                f"The text has {len(segmented.segments)} sentences; the limit is {cfg.max_segments}. Split it into parts.",
                code="too_many_segments",
                extra={"max_segments": cfg.max_segments, "segments": len(segmented.segments)},
            )
        generation = request.generation or cfg.default_generation
        source_texts = segmented.texts()
        current = source_texts
        legs: list[LegResult] = []
        for leg in plan.legs:
            current, leg_result = await self._run_leg(leg, current, generation)
            legs.append(leg_result)

        translation = segmented.render(current)
        warnings = self._validate(source_texts, current, request.target, translation)
        timings["queue_wait_ms"] = _ms(sum(leg.queue_wait_s for leg in legs))
        timings["model_load_ms"] = _ms(sum(leg.load_s for leg in legs))
        timings["inference_ms"] = _ms(sum(leg.inference_s for leg in legs))
        timings["total_ms"] = _ms(clock() - started)
        log_event(
            logger, logging.INFO, "translate.done", source=source, target=request.target,
            models=[leg.model_id for leg in legs], pivot=plan.pivot_via, chars=len(norm.text),
            segments=len(source_texts), warnings=[w.code for w in warnings], total_ms=timings["total_ms"],
        )
        return TranslationResult(
            translation=translation,
            source_language=source,
            source_detection=detection,
            target_language=request.target,
            legs=tuple(legs),
            pivot_via=plan.pivot_via,
            segments=len(source_texts),
            input_chars=len(norm.text),
            output_chars=len(translation),
            warnings=tuple(warnings),
            timings_ms=timings,
            normalization=dict(norm.stats),
        )

    # -- internals ---------------------------------------------------------------------------
    def _resolve_source(self, detection: DetectionResult) -> str:
        if detection.status == "resolved" and detection.language:
            return detection.language
        if detection.status == "unsupported_language":
            names = ", ".join(detection.unlisted_candidates) or detection.language or "unknown"
            raise UnsupportedLanguageError(
                f"The text is in a script used by a language that is not in the registry ({names}).",
                extra={"language": detection.language, "script": detection.script},
            )
        raise LanguageAmbiguousError(
            "The source language could not be determined from the text alone. Choose it manually.",
            extra={
                "status": detection.status,
                "script": detection.script,
                "candidates": list(detection.candidates),
                "unlisted_candidates": list(detection.unlisted_candidates),
                "suggested": detection.suggested,
                "notes": list(detection.notes),
            },
        )

    async def _run_leg(self, leg: Route, segment_texts: Sequence[str], generation: GenerationParams) -> tuple[list[str], LegResult]:
        cfg = self._config
        spec = leg.spec
        models = self._models

        def job(cancel: CancelToken) -> _LegOutput:
            try:
                backend, load_s = models.acquire(spec)
                src_code, tgt_code = spec.model_code(leg.source), spec.model_code(leg.target)
                if backend.supports_token_count:
                    def counter(text: str) -> int:
                        return backend.count_tokens(text, src_code)
                    basis = "tokenizer"
                else:
                    counter = estimate_tokens
                    basis = "estimate"
                units = plan_units(list(segment_texts), count_tokens=counter, max_tokens=spec.segment_token_limit)
                batches = plan_batches(
                    units, count_tokens=counter, max_batch_size=cfg.max_batch_size, max_batch_tokens=cfg.max_batch_tokens
                )
                results: list[str] = [""] * len(units)
                begun = time.perf_counter()
                for batch in batches:
                    cancel.raise_if_cancelled()
                    texts = [units[i].text for i in batch]
                    out = backend.translate_batch(texts, src_code, tgt_code, generation)
                    if len(out) != len(texts):
                        raise InferenceError("The model returned a different number of sentences than it was given.", code="batch_size_mismatch")
                    for index, translated in zip(batch, out, strict=True):
                        results[index] = translated
                inference_s = time.perf_counter() - begun
                merged = merge_units(units, results, len(segment_texts))
                splits = Counter(u.split for u in units if u.split)
                return _LegOutput(merged, len(units), len(batches), dict(splits), basis, load_s, inference_s, backend.device)
            except PlatformError:
                raise
            except MemoryError:
                raise InferenceError("Not enough memory to translate this text.", code="out_of_memory") from None
            except Exception as exc:  # noqa: BLE001 - library messages may quote the input, so they are not surfaced
                logger.error("inference.failed", exc_info=True, extra={"fields": {"model_id": spec.id, "exc_type": type(exc).__name__}})
                code = "out_of_memory" if "out of memory" in str(exc).lower() else "inference_failed"
                raise InferenceError(
                    "The model failed while translating. Details are in the server log.",
                    code=code, extra={"model_id": spec.id, "error_type": type(exc).__name__},
                ) from exc

        job_result = await self._executor.run(job, timeout=cfg.job_timeout_s)
        out = job_result.value
        leg_result = LegResult(
            source=leg.source, target=leg.target, model_id=spec.id, model_revision=spec.revision,
            licence=spec.licence.spdx, device=out.device, units=out.units, batches=out.batches,
            split_units=out.split_units, token_counts=out.token_counts, queue_wait_s=job_result.queued_s,
            load_s=out.load_s, inference_s=out.inference_s,
        )
        return out.texts, leg_result

    def _validate(self, inputs: Sequence[str], outputs: Sequence[str], target: str, translation: str) -> list[ResultWarning]:
        """Hard failures for unusable output; warnings (never scores) for suspicious output."""
        empty = [i for i, (src, out) in enumerate(zip(inputs, outputs, strict=True)) if src.strip() and not out.strip()]
        if empty:
            raise OutputValidationError(
                "The model returned an empty translation for some sentences.",
                code="empty_output", extra={"segment_indexes": empty[:50], "count": len(empty)},
            )
        warnings: list[ResultWarning] = []
        outliers = [
            i for i, (src, out) in enumerate(zip(inputs, outputs, strict=True))
            if (len(out) / max(1, len(src)) > 8) or (len(src) >= 20 and len(out) / len(src) < 0.1)
        ]
        if outliers:
            warnings.append(ResultWarning("length_ratio_outlier", "Some translations are far longer or shorter than their source.", len(outliers)))
        copied = [
            i for i, (src, out) in enumerate(zip(inputs, outputs, strict=True))
            if src == out and profile_text(src).total >= 4
        ]
        if copied:
            warnings.append(ResultWarning("source_copied", "Some sentences came back unchanged.", len(copied)))
        language = self._registry.language(target)
        profile = profile_text(translation)
        if language is not None and profile.total >= 8:
            share = sum(profile.share(script) for script in language.scripts)
            if share < self._config.min_target_script_share:
                warnings.append(
                    ResultWarning(
                        "target_script_mismatch",
                        f"Only {share:.0%} of the output letters are in the expected script for {language.name}.",
                    )
                )
        return warnings
