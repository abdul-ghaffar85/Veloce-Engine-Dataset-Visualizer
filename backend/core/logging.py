# ═══════════════════════════════════════════════════════════════════════════════
# Veloce Engine — Structured Logging
# ═══════════════════════════════════════════════════════════════════════════════
"""
Production-grade structured logging built on ``structlog``.

Features:

* **JSON output** in production / staging for log aggregators (ELK, Datadog).
* **Coloured console output** in development for readability.
* **Correlation IDs** injected via middleware and propagated to every log line.
* **Contextual enrichment** — each log event carries ``app_name``, ``app_env``,
  ``logger``, ``timestamp``, and optional ``request_id``.
* **File rotation** support via ``logging.handlers.RotatingFileHandler``.
* **FastAPI middleware** that auto-generates and injects ``X-Request-ID``.

Usage::

    from backend.core.logging import get_logger

    logger = get_logger(__name__)
    logger.info("dataset_uploaded", filename="sales.csv", rows=42_000)

Middleware registration::

    from backend.core.logging import RequestIdMiddleware

    app.add_middleware(RequestIdMiddleware)
"""

from __future__ import annotations

import logging
import logging.handlers
import sys
import uuid
from contextvars import ContextVar
from pathlib import Path
from typing import Any

import structlog
from starlette.middleware.base import BaseHTTPMiddleware, RequestResponseEndpoint
from starlette.requests import Request
from starlette.responses import Response

from backend.core.config import settings

# ─── Correlation ID Context ──────────────────────────────────────────────────

_request_id_ctx: ContextVar[str | None] = ContextVar(
    "request_id", default=None
)


def get_request_id() -> str | None:
    """Return the correlation ID for the current async context, if any."""
    return _request_id_ctx.get()


def set_request_id(request_id: str) -> None:
    """Bind a correlation ID for the current async context."""
    _request_id_ctx.set(request_id)


# ─── Structlog Processors ────────────────────────────────────────────────────

def _add_request_id(
    _logger: Any,
    _method_name: str,
    event_dict: dict[str, Any],
) -> dict[str, Any]:
    """Inject the current correlation ID into every log event."""
    request_id = get_request_id()
    if request_id is not None:
        event_dict["request_id"] = request_id
    return event_dict


def _add_app_context(
    _logger: Any,
    _method_name: str,
    event_dict: dict[str, Any],
) -> dict[str, Any]:
    """Inject application metadata into every log event."""
    event_dict["app_name"] = settings.APP_NAME
    event_dict["app_env"] = settings.APP_ENV.value
    return event_dict


# ─── Logging Setup ───────────────────────────────────────────────────────────

def _configure_stdlib_logging() -> None:
    """
    Configure Python's stdlib ``logging`` as the sink for structlog.

    * Sets the root logger level from config.
    * Adds a stderr ``StreamHandler``.
    * Optionally adds a ``RotatingFileHandler`` if ``LOG_FILE`` is set.
    """
    root = logging.getLogger()
    root.setLevel(settings.LOG_LEVEL)

    # Remove any existing handlers to prevent duplication on re-init.
    root.handlers.clear()

    # ── Console handler ──────────────────────────────────────────────
    console_handler = logging.StreamHandler(sys.stderr)
    console_handler.setLevel(settings.LOG_LEVEL)
    root.addHandler(console_handler)

    # ── File handler (optional) ──────────────────────────────────────
    log_file = settings.resolved_log_file
    if log_file is not None:
        log_file.parent.mkdir(parents=True, exist_ok=True)
        file_handler = logging.handlers.RotatingFileHandler(
            filename=str(log_file),
            maxBytes=50 * 1024 * 1024,  # 50 MB per file
            backupCount=5,
            encoding="utf-8",
        )
        file_handler.setLevel(settings.LOG_LEVEL)
        root.addHandler(file_handler)

    # Silence noisy third-party loggers.
    for noisy in ("uvicorn.access", "httpcore", "httpx"):
        logging.getLogger(noisy).setLevel(logging.WARNING)


def setup_logging() -> None:
    """
    Initialise the full logging stack.

    Must be called **once** during application startup (typically inside the
    FastAPI lifespan context manager).  Safe to call multiple times — will
    reset and reconfigure cleanly.
    """
    _configure_stdlib_logging()

    # ── Shared processors (run for every log event) ──────────────────
    shared_processors: list[structlog.types.Processor] = [
        structlog.contextvars.merge_contextvars,
        _add_request_id,
        _add_app_context,
        structlog.stdlib.add_log_level,
        structlog.stdlib.add_logger_name,
        structlog.processors.TimeStamper(fmt="iso"),
        structlog.processors.StackInfoRenderer(),
        structlog.processors.UnicodeDecoder(),
    ]

    # ── Renderer: JSON for production, coloured console for dev ──────
    if settings.LOG_FORMAT.value == "json":
        renderer: structlog.types.Processor = structlog.processors.JSONRenderer()
    else:
        renderer = structlog.dev.ConsoleRenderer(colors=True)

    structlog.configure(
        processors=[
            *shared_processors,
            structlog.stdlib.ProcessorFormatter.wrap_for_formatter,
        ],
        logger_factory=structlog.stdlib.LoggerFactory(),
        wrapper_class=structlog.stdlib.BoundLogger,
        cache_logger_on_first_use=True,
    )

    # Apply the structlog formatter to all stdlib handlers.
    formatter = structlog.stdlib.ProcessorFormatter(
        processors=[
            structlog.stdlib.ProcessorFormatter.remove_processors_meta,
            renderer,
        ],
    )
    for handler in logging.getLogger().handlers:
        handler.setFormatter(formatter)


# ─── Logger Factory ───────────────────────────────────────────────────────────

def get_logger(name: str | None = None) -> structlog.stdlib.BoundLogger:
    """
    Obtain a structured logger bound to the given name.

    Args:
        name: Typically ``__name__`` of the calling module.

    Returns:
        A structlog ``BoundLogger`` that writes through stdlib ``logging``.
    """
    return structlog.get_logger(name)  # type: ignore[return-value]


# ─── Request ID Middleware ────────────────────────────────────────────────────

class RequestIdMiddleware(BaseHTTPMiddleware):
    """
    Starlette middleware that ensures every request carries a correlation ID.

    * If the client sends ``X-Request-ID``, that value is reused.
    * Otherwise, a new UUID-4 is generated.
    * The ID is stored in a ``ContextVar`` so all downstream log calls
      automatically include it.
    * The ID is returned in the ``X-Request-ID`` response header for tracing.
    """

    async def dispatch(
        self,
        request: Request,
        call_next: RequestResponseEndpoint,
    ) -> Response:
        request_id = request.headers.get(
            "x-request-id", uuid.uuid4().hex
        )
        set_request_id(request_id)

        logger = get_logger("http")
        logger.info(
            "request_started",
            method=request.method,
            path=str(request.url.path),
            client=request.client.host if request.client else "unknown",
        )

        response: Response = await call_next(request)

        logger.info(
            "request_completed",
            method=request.method,
            path=str(request.url.path),
            status_code=response.status_code,
        )

        response.headers["X-Request-ID"] = request_id
        return response
