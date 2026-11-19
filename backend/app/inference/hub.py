"""Hugging Face cache checks. Never touches the network."""

from __future__ import annotations

import threading
import time
from collections.abc import Callable

from ..domain.models import ModelSpec


def is_model_downloaded(spec: ModelSpec) -> bool:
    """True when a snapshot of the model exists in the local Hugging Face cache (a presence check, not an integrity check)."""
    try:
        from huggingface_hub import snapshot_download
    except ImportError:
        return False
    try:
        snapshot_download(spec.hf_repo, revision=spec.revision, local_files_only=True)
        return True
    except Exception:  # noqa: BLE001 - any failure means "not usable locally"
        return False


class AvailabilityCache:
    """Caches cache-presence checks for a short time so routing a request does not hit the disk 8 times."""

    def __init__(self, checker: Callable[[ModelSpec], bool] = is_model_downloaded, *, ttl_s: float = 30.0,
                 clock: Callable[[], float] = time.monotonic) -> None:
        self._checker = checker
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
