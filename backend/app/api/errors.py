"""RFC 9457 problem+json error responses. Messages never include user text, paths or stack traces."""

from __future__ import annotations

import logging

from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from starlette.exceptions import HTTPException as StarletteHTTPException

from ..core.errors import PlatformError, QueueFullError
from ..core.logging import request_id_var

logger = logging.getLogger(__name__)
PROBLEM_JSON = "application/problem+json"


def problem_response(error: PlatformError, request_id: str | None) -> JSONResponse:
    headers: dict[str, str] = {}
    if isinstance(error, QueueFullError):
        headers["Retry-After"] = str(error.extra.get("retry_after", 5))
    return JSONResponse(error.to_problem(request_id), status_code=error.status, media_type=PROBLEM_JSON, headers=headers)


def _generic(status: int, code: str, title: str, detail: str, extra: dict | None = None) -> JSONResponse:
    body = {"type": f"urn:mlai:error:{code}", "title": title, "status": status, "detail": detail, "code": code}
    rid = request_id_var.get()
    if rid:
        body["request_id"] = rid
    body.update(extra or {})
    return JSONResponse(body, status_code=status, media_type=PROBLEM_JSON)


def install_exception_handlers(app: FastAPI) -> None:
    @app.exception_handler(PlatformError)
    async def _platform_error(request: Request, exc: PlatformError) -> JSONResponse:
        return problem_response(exc, request_id_var.get())

    @app.exception_handler(RequestValidationError)
    async def _validation_error(request: Request, exc: RequestValidationError) -> JSONResponse:
        # Pydantic's default body echoes the offending input, which may be user text. Keep location, message and type only.
        problems = [
            {"loc": [str(part) for part in err.get("loc", ())], "msg": str(err.get("msg", "")), "type": str(err.get("type", ""))}
            for err in exc.errors()
        ]
        return _generic(422, "validation_error", "Request validation failed", "One or more fields are invalid.", {"errors": problems})

    @app.exception_handler(StarletteHTTPException)
    async def _http_error(request: Request, exc: StarletteHTTPException) -> JSONResponse:
        titles = {404: "Not found", 405: "Method not allowed"}
        return _generic(exc.status_code, f"http_{exc.status_code}", titles.get(exc.status_code, "HTTP error"), "The request could not be served.")

    @app.exception_handler(Exception)
    async def _unexpected(request: Request, exc: Exception) -> JSONResponse:
        logger.error("unhandled.exception", exc_info=True, extra={"fields": {"exc_type": type(exc).__name__, "path": request.url.path}})
        return _generic(500, "internal_error", "Internal error", "Something went wrong on the server. Quote the request id when reporting it.")
