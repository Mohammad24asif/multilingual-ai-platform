#!/usr/bin/env python3
"""Run a few real translations through the full pipeline (router -> worker -> model -> validation).

This is the first check to run on your machine after downloading a model. It prints what ran, how
long it took and any warnings, and can save a JSON report you can send back for debugging.
"""

import argparse
import asyncio
import json
import time
from datetime import UTC, datetime
from pathlib import Path

import _paths  # noqa: F401

from app.config import Settings
from app.core.errors import PlatformError
from app.core.logging import configure_logging
from app.presentation import present_translation
from app.runtime import Container
from app.translation.types import TranslationRequest

SAMPLES = [
    ("en", "te", "The weather is pleasant today, and we are going to the market."),
    ("te", "en", "ఈ రోజు వాతావరణం చాలా బాగుంది."),
    ("hi", "en", "आज मौसम बहुत अच्छा है।"),
    ("en", "ur", "How are you today?"),
]


async def run(container: Container, model_id: str | None, pairs: list[tuple[str, str, str]]) -> list[dict]:
    rows = []
    for source, target, text in pairs:
        began = time.perf_counter()
        try:
            result = await container.translation.translate(TranslationRequest(text, target=target, source=source, model_id=model_id))
            payload = present_translation(result, container.registry)
            print(f"[ok]   {source}->{target}  {payload['legs'][0]['model_id']}  {payload['timings_ms']['total_ms']} ms  warnings={[w['code'] for w in payload['warnings']]}")
            print(f"       {text}\n    -> {payload['translation']}")
            rows.append({"source": source, "target": target, "ok": True, "result": payload})
        except PlatformError as exc:
            print(f"[fail] {source}->{target}  {exc.code}: {exc.detail}")
            rows.append({"source": source, "target": target, "ok": False, "error": exc.to_problem()})
        print(f"       (wall time {time.perf_counter() - began:.1f} s)")
    return rows


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--model", help="force one registry model id")
    parser.add_argument("--report", help="write a JSON report to this path")
    args = parser.parse_args()
    settings = Settings()
    configure_logging("WARNING", json_output=False)
    container = Container(settings.to_runtime())
    container.start()
    try:
        print(f"device={container.device} licence_mode={settings.licence_mode} downloads_allowed={settings.allow_model_download}")
        ready = container.readiness()
        if not ready["ready"]:
            print("Not ready:", *ready["problems"], sep="\n  ")
            return 1
        rows = asyncio.run(run(container, args.model, SAMPLES))
        if args.report:
            report = {
                "created": datetime.now(UTC).isoformat(timespec="seconds"),
                "system": container.system_overview(),
                "models": container.models_overview(),
                "samples": rows,
            }
            Path(args.report).parent.mkdir(parents=True, exist_ok=True)
            Path(args.report).write_text(json.dumps(report, indent=2, ensure_ascii=False), encoding="utf-8")
            print(f"report written to {args.report}")
        return 0 if all(r["ok"] for r in rows) else 1
    finally:
        container.stop()


if __name__ == "__main__":
    raise SystemExit(main())
