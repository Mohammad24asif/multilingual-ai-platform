"""Error types shared by every layer. Each maps to one HTTP status and one stable machine-readable code.

The API renders these as RFC 9457 "problem details" (application/problem+json). Messages must never
contain user text, file-system paths or stack traces.
"""

from __future__ import annotations

from typing import Any


class PlatformError(Exception):
    code = "internal_error"
    status = 500
    title = "Internal error"

    def __init__(self, detail: str = "", *, extra: dict[str, Any] | None = None, code: str | None = None) -> None:
        super().__init__(detail or self.title)
        self.detail = detail or self.title
        self.extra: dict[str, Any] = dict(extra or {})
        if code:
            self.code = code

    def to_problem(self, request_id: str | None = None) -> dict[str, Any]:
        body: dict[str, Any] = {
            "type": f"urn:mlai:error:{self.code}",
            "title": self.title,
            "status": self.status,
            "detail": self.detail,
            "code": self.code,
        }
        if request_id:
            body["request_id"] = request_id
        body.update(self.extra)
        return body


class InvalidInputError(PlatformError):
    code = "invalid_input"
    status = 422
    title = "Invalid input"


class UnsupportedLanguageError(PlatformError):
    code = "unsupported_language"
    status = 422
    title = "Unsupported language"


class SameLanguageError(PlatformError):
    code = "same_language"
    status = 422
    title = "Source and target language are the same"


class LanguageAmbiguousError(PlatformError):
    code = "language_ambiguous"
    status = 422
    title = "Source language could not be determined"


class UnknownModelError(PlatformError):
    code = "unknown_model"
    status = 422
    title = "Unknown model"


class UnsupportedPairError(PlatformError):
    code = "unsupported_language_pair"
    status = 422
    title = "No suitable model for this language pair"


class ModelNotDownloadedError(PlatformError):
    code = "model_not_downloaded"
    status = 503
    title = "Model weights are not downloaded"


class ModelLoadError(PlatformError):
    code = "model_load_failed"
    status = 503
    title = "Model could not be loaded"


class RemoteCodeNotAllowedError(PlatformError):
    code = "remote_code_not_allowed"
    status = 503
    title = "Model requires reviewed remote code"


class QueueFullError(PlatformError):
    code = "server_busy"
    status = 503
    title = "Inference queue is full"


class InferenceTimeoutError(PlatformError):
    code = "inference_timeout"
    status = 504
    title = "Inference timed out"


class InferenceError(PlatformError):
    code = "inference_failed"
    status = 502
    title = "Inference failed"


class OutputValidationError(PlatformError):
    code = "invalid_model_output"
    status = 502
    title = "Model produced unusable output"


class JobCancelledError(PlatformError):
    code = "cancelled"
    status = 499
    title = "Request cancelled"


class PayloadTooLargeError(PlatformError):
    code = "payload_too_large"
    status = 413
    title = "Request body is too large"


class NotFoundError(PlatformError):
    code = "not_found"
    status = 404
    title = "Not found"
