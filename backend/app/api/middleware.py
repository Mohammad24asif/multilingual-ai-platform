"""Request id, size limit, privacy-preserving access log and security headers."""

from __future__ import annotations

import logging
import re
import time
import uuid

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware

from ..core.errors import PayloadTooLargeError
from ..core.logging import log_event, request_id_var
from .errors import problem_response

logger = logging.getLogger("app.http")
_SAFE_ID = re.compile(r"^[A-Za-z0-9_-]{1,64}$")


def install_middleware(app: FastAPI, *, cors_origins: list[str], max_request_bytes: int) -> None:
    app.add_middleware(
        CORSMiddleware,
        allow_origins=cors_origins,
        allow_credentials=False,
        allow_methods=["GET", "POST", "DELETE"],
        allow_headers=["Content-Type", "X-Request-ID"],
        expose_headers=["X-Request-ID", "Retry-After"],
        max_age=600,
    )

    @app.middleware("http")
    async def request_context(request: Request, call_next):  # type: ignore[no-untyped-def]
        supplied = request.headers.get("x-request-id", "")
        request_id = supplied if _SAFE_ID.match(supplied) else uuid.uuid4().hex[:16]
        token = request_id_var.set(request_id)
        started = time.perf_counter()
        try:
            length = request.headers.get("content-length", "")
            if length.isdigit() and int(length) > max_request_bytes:
                response = problem_response(
                    PayloadTooLargeError(f"The request body is larger than {max_request_bytes} bytes."), request_id
                )
            else:
                response = await call_next(request)
            response.headers["X-Request-ID"] = request_id
            response.headers["X-Content-Type-Options"] = "nosniff"
            response.headers["Referrer-Policy"] = "no-referrer"
            if request.url.path.startswith("/api/") and not request.url.path.startswith("/api/docs"):
                response.headers["Cache-Control"] = "no-store"  # translations are private; never cache them
            log_event(
                logger, logging.INFO, "http.request", method=request.method, path=request.url.path,
                status=response.status_code, duration_ms=round((time.perf_counter() - started) * 1000, 2),
            )
            return response
        finally:
            request_id_var.reset(token)
