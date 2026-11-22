
"""Hugging Face cache checks. Never touches the network."""

from __future__ import annotations

import threading
import time
from collections.abc import Callable
from pathlib import Path

from ..domain.models import ModelSpec


def is_model_downloaded(
    spec: ModelSpec,
    *,
    require_safetensors: bool = False,
) -> bool:
    """Check for locally cached model configuration, tokenizer and usable weights."""
    try:
        from huggingface_hub import snapshot_download
    except ImportError:
        return False

    patterns = [
        "config.json",
        "generation_config.json",
        "model.safetensors",
        "model-*.safetensors",
        "*.safetensors.index.json",
        "tokenizer.json",
        "tokenizer_config.json",
        "special_tokens_map.json",
        "sentencepiece.bpe.model",
        "spiece.model",
        "vocab.json",
        "merges.txt",
        "source.spm",
        "target.spm",
    ]

    if not require_safetensors:
        patterns.extend([
            "pytorch_model.bin",
            "pytorch_model-*.bin",
            "pytorch_model.bin.index.json",
        ])

    try:
        snapshot = Path(
            snapshot_download(
                spec.hf_repo,
                revision=spec.revision,
                local_files_only=True,
                allow_patterns=patterns,
            )
        )

        if not (snapshot / "config.json").is_file():
            return False

        has_safetensors = (
            (snapshot / "model.safetensors").is_file()
            or any(snapshot.glob("model-*.safetensors"))
            or (snapshot / "model.safetensors.index.json").is_file()
        )

        has_pickle_weights = (
            (snapshot / "pytorch_model.bin").is_file()
            or any(snapshot.glob("pytorch_model-*.bin"))
            or (snapshot / "pytorch_model.bin.index.json").is_file()
        )

        if require_safetensors:
            return has_safetensors

        return has_safetensors or has_pickle_weights

    except Exception:  # noqa: BLE001 - any failure means "not usable locally"
        return False


class AvailabilityCache:
    """Cache model-presence checks so routing does not repeatedly scan the disk."""

    def __init__(
        self,
        checker: Callable[[ModelSpec], bool] | None = None,
        *,
        require_safetensors: bool = False,
        ttl_s: float = 30.0,
        clock: Callable[[], float] = time.monotonic,
    ) -> None:
        self._checker = checker or (
            lambda spec: is_model_downloaded(
                spec,
                require_safetensors=require_safetensors,
            )
        )
        self._ttl = ttl_s
        self._clock = clock
        self._entries: dict[str, tuple[float, bool]] = {}
        self._lock = threading.Lock()

    def __call__(self, spec: ModelSpec) -> bool:
        now = self._clock()
        with self._lock:
            hit = self._entries.get(spec.id)
            if hit is not None and now - hit[0] < self._ttl:
                return hit[1]

        value = bool(self._checker(spec))

        with self._lock:
            self._entries[spec.id] = (now, value)

        return value

    def invalidate(self) -> None:
        with self._lock:
            self._entries.clear()
