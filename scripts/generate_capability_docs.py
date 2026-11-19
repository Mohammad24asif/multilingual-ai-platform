#!/usr/bin/env python3
"""Regenerate docs/CAPABILITIES.md from the registry.   --check exits 1 if the committed file is stale."""

import argparse
import sys

import _paths  # noqa: F401

from app.capability_docs import render_capabilities
from app.domain.registry import Registry

TARGET = _paths.REPO_ROOT / "docs" / "CAPABILITIES.md"


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--check", action="store_true", help="fail if docs/CAPABILITIES.md is out of date")
    args = parser.parse_args()
    rendered = render_capabilities(Registry.from_dir())
    if args.check:
        current = TARGET.read_text(encoding="utf-8") if TARGET.exists() else ""
        if current != rendered:
            print("docs/CAPABILITIES.md is out of date. Run: python scripts/generate_capability_docs.py", file=sys.stderr)
            return 1
        print("docs/CAPABILITIES.md is up to date")
        return 0
    TARGET.parent.mkdir(parents=True, exist_ok=True)
    TARGET.write_text(rendered, encoding="utf-8")
    print(f"wrote {TARGET}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
