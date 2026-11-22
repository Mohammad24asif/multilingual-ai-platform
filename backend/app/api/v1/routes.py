
"""Version 1 of the REST API. Handlers are thin: parse, call the core, present.

STATUS: not executed in the build sandbox (FastAPI is not installed there). Covered by tests/api/test_api.py,
which you run on your machine (see docs/TESTING.md).
"""

from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, Depends, Query, Request
from fastapi.responses import JSONResponse

from ... import __version__
from ...presentation import present_plan, present_translation
from ...runtime import Container
from ...translation.backends.base import GenerationParams
from ...translation.types import TranslationRequest
from ..schemas import (
    DetectRequest,
    DetectResponse,
    LanguageOut,
    ModelOut,
    ProblemResponse,
    RouteResponse,
    TranslateRequest,
    TranslateResponse,
)

router = APIRouter(prefix="/api/v1")

PROBLEMS = {
    404: {"model": ProblemResponse},
    413: {"model": ProblemResponse},
    422: {"model": ProblemResponse},
    503: {"model": ProblemResponse},
    504: {"model": ProblemResponse},
}


def get_container(request: Request) -> Container:
    return request.app.state.container


ContainerDependency = Annotated[Container, Depends(get_container)]


@router.get("/health/live", tags=["health"], summary="Is the application process up?")
async def live() -> dict[str, str]:
    return {"status": "ok", "version": __version__}


@router.get("/health/ready", tags=["health"], summary="Can translation actually run right now?")
async def ready(container: ContainerDependency) -> JSONResponse:
    body = container.readiness()
    return JSONResponse(body, status_code=200 if body["ready"] else 503)


@router.get("/languages", response_model=list[LanguageOut], tags=["registry"], summary="Languages and what they can be used for")
async def languages(container: ContainerDependency) -> list[dict]:
    return container.languages_overview()


@router.get("/models", response_model=list[ModelOut], tags=["registry"], summary="Models, licences, evidence and why each is usable or blocked")
async def models(container: ContainerDependency) -> list[dict]:
    return container.models_overview()


@router.get("/system", tags=["health"], summary="Hardware, queue and policy summary")
async def system(container: ContainerDependency) -> dict:
    return container.system_overview()


@router.get("/route", response_model=RouteResponse, responses=PROBLEMS, tags=["translation"], summary="Which model(s) would translate this pair, and why")
async def route(
    container: ContainerDependency,
    source: str = Query(min_length=2, max_length=8),
    target: str = Query(min_length=2, max_length=8),
    model_id: str | None = Query(default=None, max_length=100),
    allow_pivot: bool = False,
) -> dict:
    return present_plan(container.translation.explain_route(source, target, model_id=model_id, allow_pivot=allow_pivot))


@router.post("/detect", response_model=DetectResponse, responses=PROBLEMS, tags=["translation"], summary="Identify the script and, when the evidence allows, the language")
async def detect(body: DetectRequest, container: ContainerDependency) -> dict:
    return container.detect(body.text)


@router.post("/translate", response_model=TranslateResponse, responses=PROBLEMS, tags=["translation"], summary="Translate text")
async def translate(body: TranslateRequest, container: ContainerDependency) -> dict:
    generation = GenerationParams(num_beams=body.num_beams) if body.num_beams else None
    request = TranslationRequest(
        text=body.text,
        target=body.target_language,
        source=body.source_language,
        model_id=body.model_id,
        allow_pivot=body.allow_pivot,
        generation=generation,
    )
    result = await container.translation.translate(request)
    return present_translation(result, container.registry)
