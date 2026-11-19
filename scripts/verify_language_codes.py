#!/usr/bin/env python3
"""Check every language code in the registry against the real tokenizer of each downloaded model.

A code the tokenizer does not know would silently map to <unk>, so this is a real verification step.
Only models whose weights are already downloaded are checked (nothing is fetched).
"""

import _paths  # noqa: F401

from app.domain.registry import Registry
from app.inference.hub import is_model_downloaded


def main() -> int:
    from transformers import AutoTokenizer

    bad = 0
    for spec in Registry.from_dir().models():
        if spec.requires_remote_code:
            print(f"skip     {spec.id} (remote code: review and allow it first)")
            continue
        if not is_model_downloaded(spec):
            print(f"skip     {spec.id} (not downloaded)")
            continue
        kwargs = {"local_files_only": True}
        if spec.revision:
            kwargs["revision"] = spec.revision
        tokenizer = AutoTokenizer.from_pretrained(spec.hf_repo, **kwargs)
        missing = []
        for platform_code, model_code in spec.language_codes.items():
            token_id = tokenizer.convert_tokens_to_ids(model_code)
            if token_id is None or token_id == tokenizer.unk_token_id:
                missing.append(f"{platform_code}->{model_code}")
        if missing:
            bad += 1
            print(f"FAILED   {spec.id}: unknown to the tokenizer: {', '.join(missing)}")
        else:
            print(f"verified {spec.id}: all {len(spec.language_codes)} codes exist in the tokenizer")
    return 1 if bad else 0


if __name__ == "__main__":
    raise SystemExit(main())
