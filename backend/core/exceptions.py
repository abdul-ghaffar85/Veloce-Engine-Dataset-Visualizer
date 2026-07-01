# ═══════════════════════════════════════════════════════════════════════════════
# Veloce Engine — Exception Hierarchy & Centralised Error Handling
# ═══════════════════════════════════════════════════════════════════════════════
"""
Domain exception taxonomy with automatic FastAPI error-response generation.

Design goals:

1. **Every domain error** extends :class:`VeloceError` so handlers catch them
   uniformly.
2. **HTTP semantics** (status code, error code string) are co-located with the
   exception, not scattered across route handlers.
3. **Sanitised responses** — internal details, stack traces, and file paths
   are *never* exposed to clients.  In development mode, a ``debug`` field
   is conditionally included for developer convenience.
4. **Structured logging** — every handled exception is logged with its full
   context (including correlation ID) before the sanitised response is sent.

Usage::

    from backend.core.exceptions import DatasetNotFoundError

    raise DatasetNotFoundError(dataset_id="abc-123")

    # → HTTP 404
    # {
    #   "error": "DATASET_NOT_FOUND",
    #   "message": "The requested dataset was not found.",
    #   "detail": {"dataset_id": "abc-123"}
    # }

Registration::

    from backend.core.exceptions import register_exception_handlers

    register_exception_handlers(app)
"""

from __future__ import annotations

import traceback
from http import HTTPStatus
from typing import Any

from fastapi import FastAPI, Request
from fastapi.responses import ORJSONResponse
from pydantic import BaseModel

from backend.core.config import settings
from backend.core.logging import get_logger

_logger = get_logger(__name__)


# ═══════════════════════════════════════════════════════════════════════════════
# Error Response Schema
# ═══════════════════════════════════════════════════════════════════════════════

class ErrorResponse(BaseModel):
    """
    Wire-format for every error returned by the API.

    Clients can programmatically branch on ``error`` (a stable code string)
    while ``message`` provides a human-readable explanation.
    """

    error: str
    message: str
    detail: dict[str, Any] | None = None
    debug: str | None = None  # populated only in development


# ═══════════════════════════════════════════════════════════════════════════════
# Base Exception
# ═══════════════════════════════════════════════════════════════════════════════

class VeloceError(Exception):
    """
    Root of the Veloce domain exception hierarchy.

    Subclasses declare their HTTP status code and a stable ``error_code``
    string.  The centralised handler maps any ``VeloceError`` to a
    consistent JSON error response.

    Args:
        message:     Human-readable description (safe to show the client).
        error_code:  Machine-readable code (e.g. ``"DATASET_NOT_FOUND"``).
        status_code: HTTP status code.
        detail:      Arbitrary dict of contextual information for the client.
        internal:    Internal-only detail for logging (never sent to client).
    """

    def __init__(
        self,
        message: str = "An unexpected error occurred.",
        *,
        error_code: str = "INTERNAL_ERROR",
        status_code: int = HTTPStatus.INTERNAL_SERVER_ERROR,
        detail: dict[str, Any] | None = None,
        internal: str | None = None,
    ) -> None:
        super().__init__(message)
        self.message = message
        self.error_code = error_code
        self.status_code = status_code
        self.detail = detail
        self.internal = internal


# ═══════════════════════════════════════════════════════════════════════════════
# Configuration Errors
# ═══════════════════════════════════════════════════════════════════════════════

class ConfigurationError(VeloceError):
    """Raised when a required configuration value is missing or invalid."""

    def __init__(
        self,
        message: str = "Invalid or missing configuration.",
        **kwargs: Any,
    ) -> None:
        super().__init__(
            message,
            error_code="CONFIGURATION_ERROR",
            status_code=HTTPStatus.INTERNAL_SERVER_ERROR,
            **kwargs,
        )


# ═══════════════════════════════════════════════════════════════════════════════
# Validation Errors
# ═══════════════════════════════════════════════════════════════════════════════

class ValidationError(VeloceError):
    """Raised when user-supplied input fails validation."""

    def __init__(
        self,
        message: str = "The request contains invalid data.",
        **kwargs: Any,
    ) -> None:
        super().__init__(
            message,
            error_code="VALIDATION_ERROR",
            status_code=HTTPStatus.UNPROCESSABLE_ENTITY,
            **kwargs,
        )


# ═══════════════════════════════════════════════════════════════════════════════
# File / Upload Errors
# ═══════════════════════════════════════════════════════════════════════════════

class FileUploadError(VeloceError):
    """Raised when a file upload fails validation or processing."""

    def __init__(
        self,
        message: str = "File upload failed.",
        **kwargs: Any,
    ) -> None:
        super().__init__(
            message,
            error_code="FILE_UPLOAD_ERROR",
            status_code=HTTPStatus.BAD_REQUEST,
            **kwargs,
        )


class FileTooLargeError(FileUploadError):
    """Raised when an uploaded file exceeds the maximum allowed size."""

    def __init__(
        self,
        max_bytes: int | None = None,
        **kwargs: Any,
    ) -> None:
        limit = max_bytes or settings.MAX_UPLOAD_SIZE_BYTES
        limit_mb = limit / (1024 * 1024)
        super().__init__(
            message=f"File exceeds the maximum allowed size of {limit_mb:.0f} MB.",
            detail={"max_bytes": limit},
            **kwargs,
        )
        self.error_code = "FILE_TOO_LARGE"
        self.status_code = HTTPStatus.REQUEST_ENTITY_TOO_LARGE


class UnsupportedFileTypeError(FileUploadError):
    """Raised when an uploaded file has a disallowed MIME type or extension."""

    def __init__(
        self,
        filename: str | None = None,
        allowed_types: list[str] | None = None,
        **kwargs: Any,
    ) -> None:
        allowed = allowed_types or [".csv", ".xlsx", ".xls"]
        super().__init__(
            message="Unsupported file type. Allowed types: "
            + ", ".join(allowed)
            + ".",
            detail={"filename": filename, "allowed_types": allowed},
            **kwargs,
        )
        self.error_code = "UNSUPPORTED_FILE_TYPE"


# ═══════════════════════════════════════════════════════════════════════════════
# Resource / Not Found Errors
# ═══════════════════════════════════════════════════════════════════════════════

class ResourceNotFoundError(VeloceError):
    """Raised when a requested resource does not exist."""

    def __init__(
        self,
        resource: str = "Resource",
        identifier: str | None = None,
        **kwargs: Any,
    ) -> None:
        msg = f"{resource} not found."
        detail: dict[str, Any] = {"resource": resource}
        if identifier is not None:
            msg = f"{resource} '{identifier}' not found."
            detail["identifier"] = identifier
        super().__init__(
            message=msg,
            error_code="RESOURCE_NOT_FOUND",
            status_code=HTTPStatus.NOT_FOUND,
            detail=detail,
            **kwargs,
        )


class DatasetNotFoundError(ResourceNotFoundError):
    """Raised when a requested dataset does not exist."""

    def __init__(self, dataset_id: str, **kwargs: Any) -> None:
        super().__init__(
            resource="Dataset",
            identifier=dataset_id,
            **kwargs,
        )
        self.error_code = "DATASET_NOT_FOUND"


# ═══════════════════════════════════════════════════════════════════════════════
# Processing Errors
# ═══════════════════════════════════════════════════════════════════════════════

class DataProcessingError(VeloceError):
    """Raised when a data processing or analysis operation fails."""

    def __init__(
        self,
        message: str = "An error occurred while processing the data.",
        **kwargs: Any,
    ) -> None:
        super().__init__(
            message,
            error_code="DATA_PROCESSING_ERROR",
            status_code=HTTPStatus.INTERNAL_SERVER_ERROR,
            **kwargs,
        )


class ProfilingError(DataProcessingError):
    """Raised when the profiling engine encounters an unrecoverable error."""

    def __init__(self, message: str = "Data profiling failed.", **kwargs: Any) -> None:
        super().__init__(message, **kwargs)
        self.error_code = "PROFILING_ERROR"


class RelationshipDiscoveryError(DataProcessingError):
    """Raised when automated relationship discovery fails."""

    def __init__(
        self,
        message: str = "Relationship discovery failed.",
        **kwargs: Any,
    ) -> None:
        super().__init__(message, **kwargs)
        self.error_code = "RELATIONSHIP_DISCOVERY_ERROR"


# ═══════════════════════════════════════════════════════════════════════════════
# Authentication / Authorisation Errors
# ═══════════════════════════════════════════════════════════════════════════════

class AuthenticationError(VeloceError):
    """Raised when authentication credentials are missing or invalid."""

    def __init__(
        self,
        message: str = "Authentication required.",
        **kwargs: Any,
    ) -> None:
        super().__init__(
            message,
            error_code="AUTHENTICATION_ERROR",
            status_code=HTTPStatus.UNAUTHORIZED,
            **kwargs,
        )


class AuthorisationError(VeloceError):
    """Raised when the authenticated user lacks the required permissions."""

    def __init__(
        self,
        message: str = "You do not have permission to perform this action.",
        **kwargs: Any,
    ) -> None:
        super().__init__(
            message,
            error_code="AUTHORISATION_ERROR",
            status_code=HTTPStatus.FORBIDDEN,
            **kwargs,
        )


# ═══════════════════════════════════════════════════════════════════════════════
# Rate Limiting
# ═══════════════════════════════════════════════════════════════════════════════

class RateLimitExceededError(VeloceError):
    """Raised when a client exceeds the configured request rate."""

    def __init__(self, **kwargs: Any) -> None:
        super().__init__(
            message="Rate limit exceeded. Please try again later.",
            error_code="RATE_LIMIT_EXCEEDED",
            status_code=HTTPStatus.TOO_MANY_REQUESTS,
            **kwargs,
        )


# ═══════════════════════════════════════════════════════════════════════════════
# Centralised Exception Handlers
# ═══════════════════════════════════════════════════════════════════════════════

def _build_error_response(
    error_code: str,
    message: str,
    status_code: int,
    detail: dict[str, Any] | None = None,
    debug_info: str | None = None,
) -> ORJSONResponse:
    """
    Construct a sanitised :class:`ORJSONResponse`.

    The ``debug`` field is included only when ``APP_DEBUG`` is ``True``.
    """
    body = ErrorResponse(
        error=error_code,
        message=message,
        detail=detail,
        debug=debug_info if settings.APP_DEBUG else None,
    )
    return ORJSONResponse(
        status_code=status_code,
        content=body.model_dump(exclude_none=True),
    )


async def _handle_veloce_error(
    request: Request,
    exc: VeloceError,
) -> ORJSONResponse:
    """Handle all domain exceptions with structured logging + sanitised response."""
    _logger.warning(
        "domain_error",
        error_code=exc.error_code,
        message=exc.message,
        detail=exc.detail,
        internal=exc.internal,
        path=str(request.url.path),
        method=request.method,
    )
    if exc.status_code == HTTPStatus.INTERNAL_SERVER_ERROR:
        return ORJSONResponse(
            status_code=exc.status_code,
            content={
                "success": False,
                "error": exc.message,
                "location": str(request.url.path),
                "exception": type(exc).__name__
            }
        )
    return _build_error_response(
        error_code=exc.error_code,
        message=exc.message,
        status_code=exc.status_code,
        detail=exc.detail,
        debug_info=exc.internal,
    )


async def _handle_unhandled_exception(
    request: Request,
    exc: Exception,
) -> ORJSONResponse:
    """
    Catch-all for unhandled exceptions.

    * Logs the full traceback for debugging.
    * Returns a generic message to the client — **never** leaks internals.
    """
    _logger.exception(
        "unhandled_exception",
        exc_type=type(exc).__name__,
        path=str(request.url.path),
        method=request.method,
        exc_info=True,
    )
    return ORJSONResponse(
        status_code=HTTPStatus.INTERNAL_SERVER_ERROR,
        content={
            "success": False,
            "error": str(exc) if settings.APP_DEBUG else "An unexpected internal error occurred.",
            "location": str(request.url.path),
            "exception": type(exc).__name__
        }
    )


def register_exception_handlers(app: FastAPI) -> None:
    """
    Register all centralised exception handlers on the FastAPI application.

    Call this once during application startup.
    """
    app.add_exception_handler(VeloceError, _handle_veloce_error)  # type: ignore[arg-type]
    app.add_exception_handler(Exception, _handle_unhandled_exception)  # type: ignore[arg-type]
