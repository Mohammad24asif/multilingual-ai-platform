"""Wires the framework-free core together. Plain-Python configuration in, ready-to-use services out."""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from .detection.detector import LanguageDetector
from .domain.models import ModelSpec
from .domain.registry import DEFAULT_REGISTRY_DIR, Registry
from .inference.executor import InferenceExecutor
from .inference.hub import AvailabilityCache
from .inference.manager import ModelManager
from .inference.system_info import choose_device, get_system_info
from .presentation import present_detection, present_language, present_model
from .translation.backends.base import BackendContext, GenerationParams, TranslationBackend
from .translation.backends.transformers_backends import make_backend_factory
from .translation.router import RoutingPolicy, TranslationRouter
from .translation.service import TranslationService
from .translation.types import TranslationConfig


@dataclass(frozen=True, slots=True)
class RuntimeConfig:
    licence_mode: str = "research"
    device: str = "auto"
    allow_model_download: bool = False
    enabled_models: frozenset[str] | None = None
    remote_code_allowlist: frozenset[str] = frozenset()
    ram_budget_mb: int | None = None
    max_loaded_models: int = 1
    inference_queue_size: int = 8
    inference_timeout_s: float = 120.0
    torch_threads: int | None = None
    max_input_chars: int = 20_000
    max_segments: int = 400
    max_batch_size: int = 8
    max_batch_tokens: int = 1_600
    num_beams: int = 4
    require_safetensors: bool = False
    registry_dir: Path | None = None


class Container:
    def __init__(
        self,
        config: RuntimeConfig,
        *,
        registry: Registry | None = None,
        backend_factory: Callable[[ModelSpec], TranslationBackend] | None = None,
        availability: Callable[[ModelSpec], bool] | None = None,
        device: str | None = None,
    ) -> None:
        self.config = config
        self.registry = registry or Registry.from_dir(config.registry_dir or DEFAULT_REGISTRY_DIR)
        policy = RoutingPolicy(
            licence_mode=config.licence_mode,
            enabled_models=config.enabled_models,
            ram_budget_mb=config.ram_budget_mb,
            remote_code_allowlist=config.remote_code_allowlist,
        )
        # When downloads are allowed a missing model is fetched on first use, so it counts as available.
        self.availability: Callable[[ModelSpec], bool] = availability or (
            (lambda spec: True) if config.allow_model_download else AvailabilityCache()
        )
        self.router = TranslationRouter(self.registry, policy, is_available=self.availability)
        self.device = device or choose_device(config.device)
        ctx = BackendContext(
            device=self.device, allow_download=config.allow_model_download,
            torch_threads=config.torch_threads, require_safetensors=config.require_safetensors,
        )
        factory = backend_factory or make_backend_factory(ctx, config.remote_code_allowlist)
        self.models = ModelManager(
            factory,
            max_loaded=config.max_loaded_models,
            ram_budget_mb=config.ram_budget_mb,
            is_downloaded=None if config.allow_model_download else self.availability,
        )
        self.executor = InferenceExecutor(queue_size=config.inference_queue_size, on_thread_start=self._configure_worker)
        self.detector = LanguageDetector(self.registry)
        self.translation = TranslationService(
            registry=self.registry,
            router=self.router,
            models=self.models,
            executor=self.executor,
            detector=self.detector,
            config=TranslationConfig(
                max_chars=config.max_input_chars,
                max_segments=config.max_segments,
                max_batch_size=config.max_batch_size,
                max_batch_tokens=config.max_batch_tokens,
                job_timeout_s=config.inference_timeout_s,
                default_generation=GenerationParams(num_beams=config.num_beams),
            ),
        )

    def _configure_worker(self) -> None:
        if self.config.torch_threads:
            try:
                import torch

                torch.set_num_threads(self.config.torch_threads)
            except ImportError:
                pass

    def start(self) -> None:
        self.executor.start()

    def stop(self) -> None:
        self.executor.shutdown()
        self.models.unload_all()

    # -- views used by the API ---------------------------------------------------------------
    def detect(self, text: str) -> dict[str, Any]:
        return present_detection(self.detector.detect(text), self.registry)

    def languages_overview(self) -> list[dict[str, Any]]:
        support = self.router.supported_languages()
        return [present_language(lang, support[lang.code]) for lang in self.registry.languages()]

    def models_overview(self) -> list[dict[str, Any]]:
        statuses = self.models.statuses()
        rows = []
        for spec in self.registry.models():
            blocked = self.router.policy_reasons(spec)
            downloaded = self.availability(spec)
            rows.append(
                present_model(
                    spec, enabled=self.router.is_enabled(spec), downloaded=downloaded,
                    status=statuses.get(spec.id), blocked_by=blocked,
                )
            )
        return rows

    def readiness(self) -> dict[str, Any]:
        """Application availability (liveness) is separate; this says whether translation can actually run."""
        problems: list[str] = []
        if not self.executor.alive:
            problems.append("The inference worker is not running.")
        usable = self.router.usable_models()
        if not usable:
            enabled = [s for s in self.registry.models("translate") if not self.router.policy_reasons(s, check_availability=False)]
            if enabled:
                names = ", ".join(s.id for s in enabled)
                problems.append(f"No allowed model has its weights downloaded. Run: python scripts/download_models.py --model {enabled[0].id}  (allowed: {names})")
            else:
                problems.append("No translation model is enabled and allowed under the current licence mode and safety policy.")
        return {
            "ready": not problems,
            "executor_alive": self.executor.alive,
            "usable_models": [s.id for s in usable],
            "loaded_models": self.models.loaded_ids(),
            "problems": problems,
        }

    def system_overview(self) -> dict[str, Any]:
        stats = self.executor.stats()
        policy = self.router.policy
        return {
            "hardware": get_system_info(),
            "device": self.device,
            "queue": {
                "depth": stats.queue_depth, "capacity": stats.queue_capacity, "running": stats.running,
                "completed": stats.completed, "failed": stats.failed, "rejected": stats.rejected, "cancelled": stats.cancelled,
            },
            "policy": {
                "licence_mode": policy.licence_mode,
                "ram_budget_mb": policy.ram_budget_mb,
                "max_loaded_models": self.config.max_loaded_models,
                "downloads_allowed": self.config.allow_model_download,
                "inference_timeout_s": self.config.inference_timeout_s,
                "max_input_chars": self.config.max_input_chars,
            },
        }
