"""Lazy loading, LRU caching and memory-aware eviction of model backends.

``acquire`` is only called from the inference worker thread, so loading never races with inference.
``statuses`` may be called from any thread (the API readiness endpoint) and is lock-protected.
"""

from __future__ import annotations

import logging
import threading
import time
from collections import OrderedDict
from collections.abc import Callable
from dataclasses import dataclass

from ..core.errors import ModelLoadError, ModelNotDownloadedError, PlatformError
from ..core.logging import log_event
from ..domain.models import ModelSpec
from ..translation.backends.base import TranslationBackend

logger = logging.getLogger(__name__)


@dataclass(frozen=True, slots=True)
class ModelStatus:
    model_id: str
    state: str  # "not_loaded" | "loading" | "loaded" | "failed"
    load_seconds: float | None = None
    last_error_code: str | None = None


class ModelManager:
    def __init__(
        self,
        factory: Callable[[ModelSpec], TranslationBackend],
        *,
        max_loaded: int = 1,
        ram_budget_mb: int | None = None,
        is_downloaded: Callable[[ModelSpec], bool] | None = None,
    ) -> None:
        if max_loaded < 1:
            raise ValueError("max_loaded must be >= 1")
        self._factory = factory
        self._max_loaded = max_loaded
        self._ram_budget_mb = ram_budget_mb
        self._is_downloaded = is_downloaded
        self._loaded: OrderedDict[str, TranslationBackend] = OrderedDict()
        self._status: dict[str, ModelStatus] = {}
        self._lock = threading.Lock()

    def acquire(self, spec: ModelSpec) -> tuple[TranslationBackend, float]:
        """Return (backend, seconds spent loading just now). Loads and evicts as needed."""
        with self._lock:
            backend = self._loaded.get(spec.id)
            if backend is not None:
                self._loaded.move_to_end(spec.id)
                return backend, 0.0
        if self._is_downloaded is not None and not self._is_downloaded(spec):
            raise ModelNotDownloadedError(
                f"Weights for '{spec.id}' are not downloaded.",
                extra={"model_ids": [spec.id], "hint": f"Run: python scripts/download_models.py --model {spec.id}"},
            )
        estimate = spec.estimated_ram_mb or 0
        if self._ram_budget_mb is not None and estimate > self._ram_budget_mb:
            self._set_status(ModelStatus(spec.id, "failed", last_error_code="exceeds_ram_budget"))
            raise ModelLoadError(
                f"'{spec.id}' needs about {estimate} MB but the memory budget is {self._ram_budget_mb} MB.",
                code="exceeds_ram_budget",
            )
        self._make_room(estimate)
        self._set_status(ModelStatus(spec.id, "loading"))
        started = time.perf_counter()
        try:
            backend = self._factory(spec)
            backend.load()
        except PlatformError as exc:
            self._set_status(ModelStatus(spec.id, "failed", last_error_code=exc.code))
            raise
        except MemoryError:
            self._set_status(ModelStatus(spec.id, "failed", last_error_code="out_of_memory"))
            raise ModelLoadError(f"Not enough memory to load '{spec.id}'.", code="out_of_memory") from None
        except Exception as exc:  # noqa: BLE001 - reported without the library message (may quote user paths)
            logger.exception("model load failed", extra={"fields": {"model_id": spec.id, "exc_type": type(exc).__name__}})
            self._set_status(ModelStatus(spec.id, "failed", last_error_code="load_error"))
            raise ModelLoadError(
                f"Could not load '{spec.id}'. Run scripts/smoke_translate.py for diagnostics; details are in the server log.",
                extra={"model_id": spec.id, "error_type": type(exc).__name__},
            ) from exc
        elapsed = time.perf_counter() - started
        with self._lock:
            self._loaded[spec.id] = backend
            self._status[spec.id] = ModelStatus(spec.id, "loaded", load_seconds=round(elapsed, 3))
        log_event(logger, logging.INFO, "model.loaded", model_id=spec.id, load_seconds=round(elapsed, 3), device=backend.device)
        return backend, elapsed

    def _make_room(self, incoming_mb: int) -> None:
        while True:
            with self._lock:
                if not self._loaded:
                    return
                used = sum((b.spec.estimated_ram_mb or 0) for b in self._loaded.values())
                over_count = len(self._loaded) >= self._max_loaded
                over_budget = self._ram_budget_mb is not None and used + incoming_mb > self._ram_budget_mb
                if not (over_count or over_budget):
                    return
                victim_id, victim = next(iter(self._loaded.items()))
                del self._loaded[victim_id]
                self._status[victim_id] = ModelStatus(victim_id, "not_loaded")
            self._safe_unload(victim_id, victim)

    @staticmethod
    def _safe_unload(model_id: str, backend: TranslationBackend) -> None:
        try:
            backend.unload()
            log_event(logger, logging.INFO, "model.unloaded", model_id=model_id)
        except Exception as exc:  # noqa: BLE001
            log_event(logger, logging.WARNING, "model.unload_failed", model_id=model_id, exc_type=type(exc).__name__)

    def unload_all(self) -> None:
        with self._lock:
            victims = list(self._loaded.items())
            self._loaded.clear()
            for model_id, _ in victims:
                self._status[model_id] = ModelStatus(model_id, "not_loaded")
        for model_id, backend in victims:
            self._safe_unload(model_id, backend)

    def _set_status(self, status: ModelStatus) -> None:
        with self._lock:
            self._status[status.model_id] = status

    def statuses(self) -> dict[str, ModelStatus]:
        with self._lock:
            return dict(self._status)

    def loaded_ids(self) -> list[str]:
        with self._lock:
            return list(self._loaded)
