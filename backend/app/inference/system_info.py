"""Hardware and runtime facts used by the model manager, the readiness check and the dashboard."""

from __future__ import annotations

import os
import platform
from importlib import metadata
from typing import Any


def _ram_mb() -> tuple[int | None, int | None]:
    try:
        import psutil

        mem = psutil.virtual_memory()
        return int(mem.total / 2**20), int(mem.available / 2**20)
    except ImportError:
        pass
    try:  # Linux fallback without psutil
        values: dict[str, int] = {}
        with open("/proc/meminfo", encoding="ascii") as handle:
            for line in handle:
                key, _, rest = line.partition(":")
                values[key] = int(rest.split()[0])
        return values["MemTotal"] // 1024, values.get("MemAvailable", values["MemTotal"]) // 1024
    except (OSError, KeyError, ValueError):
        return None, None


def _package_version(name: str) -> str | None:
    try:
        return metadata.version(name)
    except metadata.PackageNotFoundError:
        return None


def _torch_info() -> dict[str, Any]:
    try:
        import torch
    except ImportError:
        return {"installed": False, "cuda_available": False}
    info: dict[str, Any] = {"installed": True, "version": torch.__version__, "cuda_available": bool(torch.cuda.is_available())}
    if info["cuda_available"]:
        info["cuda_device"] = torch.cuda.get_device_name(0)
        info["cuda_memory_mb"] = int(torch.cuda.get_device_properties(0).total_memory / 2**20)
    return info


def get_system_info() -> dict[str, Any]:
    total, available = _ram_mb()
    physical = None
    try:
        import psutil

        physical = psutil.cpu_count(logical=False)
    except ImportError:
        pass
    return {
        "python": platform.python_version(),
        "platform": platform.system(),
        "machine": platform.machine(),
        "cpu_count_logical": os.cpu_count(),
        "cpu_count_physical": physical,
        "ram_total_mb": total,
        "ram_available_mb": available,
        "torch": _torch_info(),
        "packages": {name: _package_version(name) for name in ("transformers", "ctranslate2", "sacrebleu", "huggingface_hub", "fastapi")},
    }


def choose_device(preference: str, *, cuda_available: bool | None = None) -> str:
    """Resolve "auto" | "cpu" | "cuda" to a concrete device. A GPU is never required."""
    if preference not in ("auto", "cpu", "cuda"):
        raise ValueError("device must be 'auto', 'cpu' or 'cuda'")
    if preference == "cpu":
        return "cpu"
    if cuda_available is None:
        cuda_available = bool(_torch_info().get("cuda_available"))
    if preference == "cuda" and not cuda_available:
        raise ValueError("device='cuda' requested but CUDA is not available; use 'auto' or 'cpu'")
    return "cuda" if cuda_available else "cpu"
