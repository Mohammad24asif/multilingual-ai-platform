#!/usr/bin/env python3
"""Print the Python files a model repository would execute (trust_remote_code) so a human can read them.

Nothing is enabled by this script. After reading, add the printed repo@commit line to MLAI_REMOTE_CODE_ALLOWLIST.
It flags risky constructs to look at first; a clean report is NOT proof of safety - read the code.
"""

import argparse
import hashlib
import re

import _paths  # noqa: F401

from app.domain.registry import Registry

RISKY = re.compile(r"\b(os\.system|subprocess|eval\(|exec\(|__import__|socket|requests|urllib|http\.client|pickle|shutil\.rmtree|os\.environ|ctypes|base64)\b")


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--model", required=True, help="model id from the registry")
    args = parser.parse_args()
    spec = Registry.from_dir().model(args.model)
    if spec is None or not spec.requires_remote_code:
        print("that model does not use remote code (or is unknown)")
        return 2
    if not spec.revision_pinned:
        print(f"Pin it first: python scripts/pin_models.py --model {spec.id}")
        return 2
    from huggingface_hub import HfApi, hf_hub_download

    files = [f for f in HfApi().list_repo_files(spec.hf_repo, revision=spec.revision) if f.endswith(".py")]
    print(f"{spec.hf_repo} @ {spec.revision}: {len(files)} Python file(s)\n")
    for name in files:
        path = hf_hub_download(spec.hf_repo, name, revision=spec.revision)
        data = open(path, "rb").read()
        print("=" * 78)
        print(f"{name}   sha256={hashlib.sha256(data).hexdigest()[:16]}  {len(data)} bytes")
        for number, line in enumerate(data.decode("utf-8", "replace").splitlines(), 1):
            if RISKY.search(line):
                print(f"  line {number}: {line.strip()}")
    print("\nIf, after reading every file, you accept this code, set:")
    print(f"  MLAI_REMOTE_CODE_ALLOWLIST={spec.hf_repo}@{spec.revision}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
