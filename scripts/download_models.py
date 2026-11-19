#!/usr/bin/env python3
"""Download model weights into the Hugging Face cache - only after telling you the size and asking.

Prefers safetensors files. Refuses pickle-only repositories unless you pass --allow-pickle-weights.
Refuses unpinned models unless you pass --allow-unpinned (run scripts/pin_models.py first).
"""

import argparse
import fnmatch

import _paths  # noqa: F401

from app.domain.registry import Registry

SKIP_ALWAYS = ["*.h5", "*.msgpack", "*.ot", "*.onnx", "*.tflite", "flax_model*", "tf_model*", "rust_model*", "*.gguf"]
PICKLE = ["*.bin", "*.pt", "*.pth"]


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--model", action="append", required=True, help="model id (repeatable)")
    parser.add_argument("--yes", action="store_true", help="skip the confirmation prompt")
    parser.add_argument("--allow-unpinned", action="store_true")
    parser.add_argument("--allow-pickle-weights", action="store_true")
    args = parser.parse_args()
    try:
        from huggingface_hub import HfApi, snapshot_download
    except ImportError:
        print("huggingface-hub is not installed. Run: cd backend && uv sync --extra ml")
        return 2
    registry = Registry.from_dir()
    api = HfApi()
    for model_id in args.model:
        spec = registry.model(model_id)
        if spec is None:
            print(f"unknown model id: {model_id}")
            return 2
        if spec.revision is None and not args.allow_unpinned:
            print(f"{model_id} is not pinned. Run: python scripts/pin_models.py --model {model_id}   (or pass --allow-unpinned)")
            return 2
        info = api.model_info(spec.hf_repo, revision=spec.revision, files_metadata=True)
        files = info.siblings or []
        has_safetensors = any(f.rfilename.endswith(".safetensors") for f in files)
        ignore = list(SKIP_ALWAYS) + (PICKLE if has_safetensors else [])
        kept = [f for f in files if not any(fnmatch.fnmatch(f.rfilename, pat) for pat in ignore)]
        if not has_safetensors and any(fnmatch.fnmatch(f.rfilename, "*.bin") for f in kept) and not args.allow_pickle_weights:
            print(f"{model_id}: this repository only ships pickle-based weight files (*.bin). Loading them runs deserialisation code.")
            print("Re-run with --allow-pickle-weights if you accept that, or convert the weights to safetensors in an isolated environment.")
            return 2
        total_gb = sum(f.size or 0 for f in kept) / 2**30
        print(f"{spec.id}: {spec.hf_repo} @ {(spec.revision or 'main')[:12]}  licence {spec.licence.spdx}")
        print(f"  will download {len(kept)} files, about {total_gb:.2f} GB (safetensors: {has_safetensors})")
        if not args.yes and input("  Continue? [y/N] ").strip().lower() != "y":
            print("  skipped")
            continue
        path = snapshot_download(repo_id=spec.hf_repo, revision=spec.revision, ignore_patterns=ignore)
        print(f"  done: {path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
