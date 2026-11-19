"""Pydantic request/response models for the public API (OpenAPI is generated from these).

STATUS: not executed in the build sandbox (pydantic is not installed there). The shapes of the response
payloads are asserted by tests/unit/test_runtime_and_presentation.py against the presenter output.
"""

from __future__ import annotations

from typing import Any

from pydantic import BaseModel, ConfigDict, Field


class DetectRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")
    text: str = Field(min_length=1, max_length=100_000, description="Text whose language should be identified.")


class TranslateRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")
    text: str = Field(min_length=1, max_length=100_000, description="Text to translate (limits are enforced by the service).")
    target_language: str = Field(min_length=2, max_length=8, description="Registry language code, e.g. 'te'.")
    source_language: str = Field(default="auto", min_length=2, max_length=8, description="Registry language code or 'auto'.")
    model_id: str | None = Field(default=None, max_length=100, description="Force one model; it is never substituted.")
    allow_pivot: bool = Field(default=False, description="Consent to a two-step translation through English when no direct model exists.")
    num_beams: int | None = Field(default=None, ge=1, le=8, description="Beam-search width (higher is slower).")


class _Loose(BaseModel):
    model_config = ConfigDict(extra="allow")


class LanguageOut(_Loose):
    code: str
    name: str
    native_name: str
    scripts: list[str]
    rtl: bool
    can_be_source: bool
    can_be_target: bool


class ModelOut(_Loose):
    id: str
    display_name: str
    family: str
    licence: dict[str, Any]
    enabled: bool
    downloaded: bool | None
    usable: bool
    blocked_by: list[str]
    state: str


class DetectResponse(_Loose):
    status: str
    candidates: list[dict[str, Any]]
    script: str | None
    method: str | None
    notes: list[str]


class TranslateResponse(_Loose):
    translation: str
    source_language: str
    target_language: str
    pivot: bool
    pivot_via: str | None
    legs: list[dict[str, Any]]
    warnings: list[dict[str, Any]]
    timings_ms: dict[str, float]


class RouteResponse(_Loose):
    pivot: bool
    pivot_via: str | None
    legs: list[dict[str, Any]]


class ProblemResponse(BaseModel):
    model_config = ConfigDict(extra="allow")
    type: str
    title: str
    status: int
    detail: str
    code: str
    request_id: str | None = None
