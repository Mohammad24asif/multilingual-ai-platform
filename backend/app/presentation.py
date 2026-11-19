"""Turn domain objects into plain JSON-ready dictionaries (the API's view models).

Pure functions, no framework imports. Wording here is what the UI shows, so it follows the product's
voice: say what is true, never promise more than the evidence supports.
"""

from __future__ import annotations

from typing import Any

from .detection.detector import DetectionResult
from .domain.models import Language, ModelSpec
from .domain.registry import Registry
from .inference.manager import ModelStatus
from .translation.router import RoutePlan
from .translation.types import TranslationResult

RAM_BASIS = "declared parameter count x 4 bytes x 1.25 overhead (an estimate, not a measurement)"
PRIORITY_BASIS = "editorial prior; replaced by measured scores once evaluation reports exist"


def present_language(lang: Language, support: dict[str, bool]) -> dict[str, Any]:
    return {
        "code": lang.code,
        "name": lang.name,
        "native_name": lang.native_name,
        "scripts": list(lang.scripts),
        "rtl": lang.rtl,
        "can_be_source": support["source"],
        "can_be_target": support["target"],
    }


def present_model(
    spec: ModelSpec, *, enabled: bool, downloaded: bool | None, status: ModelStatus | None, blocked_by: list[str]
) -> dict[str, Any]:
    return {
        "id": spec.id,
        "display_name": spec.display_name,
        "family": spec.family,
        "task": spec.task,
        "hf_repo": spec.hf_repo,
        "revision": spec.revision,
        "revision_pinned": spec.revision_pinned,
        "licence": {
            "spdx": spec.licence.spdx,
            "class": spec.licence.klass.value,
            "verified": spec.licence.verified,
            "note": spec.licence.note,
        },
        "requires_remote_code": spec.requires_remote_code,
        "params_millions": spec.params_millions,
        "estimated_ram_mb": spec.estimated_ram_mb,
        "ram_estimate_basis": RAM_BASIS,
        "source_languages": sorted(spec.sources),
        "target_languages": sorted(spec.targets),
        "priority": spec.priority,
        "priority_basis": PRIORITY_BASIS,
        "enabled": enabled,
        "downloaded": downloaded,
        "state": status.state if status else "not_loaded",
        "last_error_code": status.last_error_code if status else None,
        "usable": not blocked_by,
        "blocked_by": blocked_by,
        "evidence": dict(spec.evidence),
        "notes": spec.notes,
    }


def present_detection(result: DetectionResult, registry: Registry) -> dict[str, Any]:
    def describe(code: str) -> dict[str, str]:
        lang = registry.language(code)
        return {"code": code, "name": lang.name if lang else code, "native_name": lang.native_name if lang else code}

    return {
        "status": result.status,
        "language": describe(result.language) if result.language and registry.language(result.language) else result.language,
        "candidates": [describe(c) for c in result.candidates],
        "unlisted_candidates": list(result.unlisted_candidates),
        "script": result.script,
        "script_share": round(result.script_share, 4),
        "scripts": [{"script": name, "share": share} for name, share in result.scripts],
        "method": result.method,
        "suggested": result.suggested,
        "notes": list(result.notes),
        "note_on_scores": "script_share is the observed fraction of letters in the dominant script, not a confidence score.",
    }


def present_plan(plan: RoutePlan) -> dict[str, Any]:
    return {
        "pivot": plan.is_pivot,
        "pivot_via": plan.pivot_via,
        "legs": [
            {
                "source": leg.source,
                "target": leg.target,
                "model_id": leg.spec.id,
                "model_name": leg.spec.display_name,
                "licence": leg.spec.licence.spdx,
                "licence_class": leg.spec.licence.klass.value,
                "considered": [
                    {"model_id": c.spec.id, "accepted": c.accepted, "reasons": list(c.reasons)} for c in leg.considered
                ],
            }
            for leg in plan.legs
        ],
    }


def present_translation(result: TranslationResult, registry: Registry) -> dict[str, Any]:
    return {
        "translation": result.translation,
        "source_language": result.source_language,
        "target_language": result.target_language,
        "source_detection": present_detection(result.source_detection, registry) if result.source_detection else None,
        "pivot": result.pivot_via is not None,
        "pivot_via": result.pivot_via,
        "legs": [
            {
                "source": leg.source,
                "target": leg.target,
                "model_id": leg.model_id,
                "model_revision": leg.model_revision,
                "licence": leg.licence,
                "device": leg.device,
                "units": leg.units,
                "batches": leg.batches,
                "split_units": leg.split_units,
                "token_counts": leg.token_counts,
                "queue_wait_ms": round(leg.queue_wait_s * 1000, 2),
                "load_ms": round(leg.load_s * 1000, 2),
                "inference_ms": round(leg.inference_s * 1000, 2),
            }
            for leg in result.legs
        ],
        "segments": result.segments,
        "input_chars": result.input_chars,
        "output_chars": result.output_chars,
        "warnings": [{"code": w.code, "detail": w.detail, "count": w.count} for w in result.warnings],
        "timings_ms": dict(result.timings_ms),
        "normalization": dict(result.normalization),
        "note": "No confidence score is reported: none of these models provides a calibrated one.",
    }
