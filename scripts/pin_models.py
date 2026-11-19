#!/usr/bin/env python3
"""Resolve each model's current commit hash and Hub licence and write backend/app/registry/models.lock.json.

Pinning makes installs reproducible and is required before any remote-code model can be enabled.
Needs internet access (and HF_TOKEN for gated repositories). Re-run it deliberately to update pins.
"""

import argparse
import json
from datetime import UTC, datetime

import _paths  # noqa: F401

from app.domain.registry import DEFAULT_REGISTRY_DIR, Registry


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--model", action="append", help="model id (repeatable); default: models enabled by default")
    parser.add_argument("--all", action="store_true", help="pin every registered model")
    args = parser.parse_args()
    try:
        from huggingface_hub import HfApi
    except ImportError:
        print("huggingface-hub is not installed. Run: cd backend && uv sync --extra ml")
        return 2
    registry = Registry.from_dir()
    if args.all:
        specs = registry.models()
    elif args.model:
        specs = []
        for model_id in args.model:
            spec = registry.model(model_id)
            if spec is None:
                print(f"unknown model id: {model_id}")
                return 2
            specs.append(spec)
    else:
        specs = [s for s in registry.models() if s.enabled_by_default]

    lock_path = DEFAULT_REGISTRY_DIR / "models.lock.json"
    lock = json.loads(lock_path.read_text(encoding="utf-8")) if lock_path.exists() else {"models": {}}
    api = HfApi()
    failures = 0
    for spec in specs:
        try:
            info = api.model_info(spec.hf_repo)
        except Exception as exc:  # noqa: BLE001 - report and continue with the next model
            print(f"FAILED   {spec.id}: {type(exc).__name__} (gated repository? set HF_TOKEN)")
            failures += 1
            continue
        card = getattr(info, "card_data", None)
        hub_licence = getattr(card, "license", None) if card is not None else None
        if isinstance(hub_licence, list):
            hub_licence = hub_licence[0] if hub_licence else None
        lock["models"][spec.id] = {
            "hf_repo": spec.hf_repo,
            "revision": info.sha,
            "hub_licence": hub_licence,
            "checked_at": datetime.now(UTC).isoformat(timespec="seconds"),
        }
        verdict = "licence matches" if hub_licence and hub_licence.lower() == spec.licence.spdx.lower() else f"LICENCE CHECK NEEDED (hub says {hub_licence!r}, registry says {spec.licence.spdx!r})"
        print(f"pinned   {spec.id:<36} {info.sha[:12]}  {verdict}")
    lock["generated_at"] = datetime.now(UTC).isoformat(timespec="seconds")
    lock_path.write_text(json.dumps(lock, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    print(f"wrote {lock_path}")
    return 1 if failures else 0


if __name__ == "__main__":
    raise SystemExit(main())
