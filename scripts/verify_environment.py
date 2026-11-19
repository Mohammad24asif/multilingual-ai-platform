#!/usr/bin/env python3
"""Check that this machine is ready to run the platform. Safe to run at any time; changes nothing."""

import importlib.util
import os
import shutil
import sys
from importlib import metadata
from pathlib import Path

import _paths  # noqa: F401

from app.domain.registry import Registry
from app.inference.hub import is_model_downloaded
from app.inference.system_info import get_system_info

REQUIRED = [
    ("fastapi", "web API"), ("uvicorn", "ASGI server"), ("pydantic", "validation"), ("pydantic_settings", "settings"),
    ("sqlalchemy", "database"), ("alembic", "migrations"), ("psutil", "hardware information"), ("huggingface_hub", "model cache and download"),
]
ML = [("torch", "PyTorch"), ("transformers", "Transformers"), ("sentencepiece", "SentencePiece tokenizers"), ("safetensors", "safe weight files")]


def version_of(module: str) -> str:
    names = {"pydantic_settings": "pydantic-settings", "huggingface_hub": "huggingface-hub"}
    try:
        return metadata.version(names.get(module, module))
    except metadata.PackageNotFoundError:
        return "?"


def check(modules: list[tuple[str, str]]) -> list[str]:
    missing = []
    for module, purpose in modules:
        if importlib.util.find_spec(module) is None:
            print(f"  MISSING  {module:<18} ({purpose})")
            missing.append(module)
        else:
            print(f"  ok       {module:<18} {version_of(module)}")
    return missing


def main() -> int:
    problems = 0
    print("== Python ==")
    py = sys.version_info
    supported = (3, 11) <= (py.major, py.minor) < (3, 14)
    print(f"  {sys.version.split()[0]} on {sys.platform}  ->  {'ok' if supported else 'UNSUPPORTED (use 3.11, 3.12 or 3.13)'}")
    problems += 0 if supported else 1

    print("== Hardware ==")
    info = get_system_info()
    print(f"  CPU threads: {info['cpu_count_logical']} (physical: {info['cpu_count_physical']})")
    print(f"  RAM: {info['ram_total_mb']} MB total, {info['ram_available_mb']} MB available")
    torch_info = info["torch"]
    print(f"  GPU: {'CUDA ' + torch_info.get('cuda_device', '') if torch_info.get('cuda_available') else 'none (CPU mode - fully supported)'}")
    cache = Path(os.environ.get("HF_HOME", Path.home() / ".cache" / "huggingface"))
    probe = cache if cache.exists() else Path.home()
    free_gb = shutil.disk_usage(probe).free / 2**30
    print(f"  Model cache: {cache}  ({free_gb:.1f} GB free; plan for 10 GB or more)")

    print("== Required packages (web API) ==")
    missing = check(REQUIRED)
    problems += len(missing)
    print("== Machine-learning packages (needed to translate) ==")
    ml_missing = check(ML)

    print("== Models ==")
    registry = Registry.from_dir()
    for spec in registry.models():
        pinned = "pinned" if spec.revision_pinned else "unpinned"
        downloaded = "downloaded" if is_model_downloaded(spec) else "not downloaded"
        default = "default" if spec.enabled_by_default else "optional"
        print(f"  {spec.id:<36} {default:<9} {pinned:<9} {downloaded}")

    print("== Next steps ==")
    if missing:
        print("  1. Install the backend:  cd backend && uv sync --extra ml")
    elif ml_missing:
        print("  1. Install the ML packages:  cd backend && uv sync --extra ml")
    else:
        print("  1. Backend packages: done")
    print("  2. Pin model revisions:   python scripts/pin_models.py")
    print("  3. Download a model:      python scripts/download_models.py --model nllb-200-distilled-600m")
    print("  4. Check real inference:  python scripts/smoke_translate.py")
    return 1 if problems else 0


if __name__ == "__main__":
    raise SystemExit(main())
