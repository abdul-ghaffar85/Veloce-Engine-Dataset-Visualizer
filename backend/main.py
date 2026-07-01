# ═══════════════════════════════════════════════════════════════════════════════
# Veloce Engine — FastAPI Application Entrypoint
# ═══════════════════════════════════════════════════════════════════════════════
"""
Application factory and entrypoint for the Veloce Engine backend.

Responsibilities:

* Assemble the FastAPI application with all middleware, exception handlers,
  and API routers.
* Execute startup / shutdown tasks via the ``lifespan`` context manager.
* Provide system-level endpoints (health check, readiness, version).

Running the server::

    uvicorn backend.main:app --reload --host 0.0.0.0 --port 8000

Or programmatically::

    python -m backend.main
"""

from __future__ import annotations

import time
from contextlib import asynccontextmanager
from pathlib import Path
from typing import AsyncIterator

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import ORJSONResponse

from backend.api.v1.routes.aggregations import router as aggregations_router
from backend.api.v1.routes.correlations import router as correlations_router
from backend.api.v1.routes.dashboards import router as dashboards_router
from backend.api.v1.routes.datasets import router as datasets_router
from backend.api.v1.routes.field_schema import router as field_schema_router
from backend.api.v1.routes.insights import router as insights_router
from backend.api.v1.routes.relationships import router as relationships_router
from backend.api.v1.routes.reports import router as reports_router
from backend.api.v1.routes.semantics import router as semantics_router
from backend.core.config import settings
from backend.core.exceptions import register_exception_handlers
from backend.core.logging import (
    RequestIdMiddleware,
    get_logger,
    setup_logging,
)
from backend.core.middleware.performance import PerformanceMetricsMiddleware

_logger = get_logger(__name__)

# ─── Startup timestamp (set once at module import) ────────────────────────────
_BOOT_TIMESTAMP: float = time.time()


# ═══════════════════════════════════════════════════════════════════════════════
# Lifespan
# ═══════════════════════════════════════════════════════════════════════════════

@asynccontextmanager
async def _lifespan(app: FastAPI) -> AsyncIterator[None]:
    """
    FastAPI lifespan context manager.

    * **Startup**: initialise logging, create upload directory, log banner.
    * **Shutdown**: perform graceful cleanup.
    """
    # ── Startup ──────────────────────────────────────────────────────────
    setup_logging()

    _logger.info(
        "application_starting",
        app_name=settings.APP_NAME,
        version=settings.APP_VERSION,
        environment=settings.APP_ENV.value,
        debug=settings.APP_DEBUG,
        host=settings.APP_HOST,
        port=settings.APP_PORT,
    )

    # Ensure the upload directory exists.
    upload_dir: Path = settings.resolved_upload_dir
    upload_dir.mkdir(parents=True, exist_ok=True)
    _logger.info("upload_directory_ready", path=str(upload_dir))

    # Ensure the log directory exists (redundant with logging setup, but
    # explicit is better than implicit).
    log_file = settings.resolved_log_file
    if log_file is not None:
        log_file.parent.mkdir(parents=True, exist_ok=True)

    _logger.info(
        "application_ready",
        cors_origins=settings.cors_origin_list,
        max_upload_mb=settings.MAX_UPLOAD_SIZE_BYTES / (1024 * 1024),
    )

    yield

    # ── Shutdown ─────────────────────────────────────────────────────────
    uptime = time.time() - _BOOT_TIMESTAMP
    _logger.info(
        "application_shutting_down",
        uptime_seconds=round(uptime, 2),
    )


# ═══════════════════════════════════════════════════════════════════════════════
# Application Factory
# ═══════════════════════════════════════════════════════════════════════════════

def create_application() -> FastAPI:
    """
    Assemble and return the fully configured FastAPI application.

    This factory pattern allows tests to instantiate isolated app instances
    with custom settings.
    """
    application = FastAPI(
        title=settings.APP_NAME,
        version=settings.APP_VERSION,
        description=(
            "AI-powered data analytics platform for CSV and Excel files. "
            "Transforms uploaded datasets into profiling, relationships, "
            "aggregations, chart recommendations, and insights."
        ),
        docs_url="/docs" if settings.APP_DEBUG else None,
        redoc_url="/redoc" if settings.APP_DEBUG else None,
        openapi_url="/openapi.json" if settings.APP_DEBUG else None,
        default_response_class=ORJSONResponse,
        lifespan=_lifespan,
    )

    # ── Middleware (order matters — outermost first) ──────────────────
    _register_middleware(application)

    # ── Exception handlers ───────────────────────────────────────────
    register_exception_handlers(application)

    # ── Routers ──────────────────────────────────────────────────────
    _register_routers(application)

    return application


# ═══════════════════════════════════════════════════════════════════════════════
# Middleware Registration
# ═══════════════════════════════════════════════════════════════════════════════

def _register_middleware(app: FastAPI) -> None:
    """
    Register all application middleware.

    Middleware is added in **reverse execution order** — the last ``add_middleware``
    call wraps the outermost layer.
    """
    # Request-ID must be outermost so the correlation ID is available to
    # every subsequent layer (including CORS error responses).
    app.add_middleware(PerformanceMetricsMiddleware)
    app.add_middleware(RequestIdMiddleware)

    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.cors_origin_list,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
        expose_headers=["X-Request-ID"],
    )


# ═══════════════════════════════════════════════════════════════════════════════
# Router Registration
# ═══════════════════════════════════════════════════════════════════════════════

def _register_routers(app: FastAPI) -> None:
    """
    Include all API routers.

    Each feature module registers its own ``APIRouter`` with a versioned
    prefix.  System routes are registered directly on the app instance.
    """
    # ── Feature routers (versioned) ──────────────────────────────────
    app.include_router(aggregations_router)
    app.include_router(correlations_router)
    app.include_router(dashboards_router)
    app.include_router(datasets_router)
    app.include_router(field_schema_router)
    app.include_router(insights_router)
    app.include_router(relationships_router)
    app.include_router(reports_router)
    app.include_router(semantics_router)

    # ── System routes (unversioned) ──────────────────────────────────
    _register_system_routes(app)


# ═══════════════════════════════════════════════════════════════════════════════
# System Endpoints
# ═══════════════════════════════════════════════════════════════════════════════

def _register_system_routes(app: FastAPI) -> None:
    """Register health, readiness, and version endpoints."""

    @app.get(
        "/health",
        tags=["System"],
        summary="Health check",
        response_class=ORJSONResponse,
    )
    async def health_check() -> dict:
        """
        Lightweight liveness probe.

        Returns HTTP 200 if the application process is alive.  This
        endpoint does **not** verify downstream dependencies — use
        ``/ready`` for that.
        """
        return {
            "status": "healthy",
            "app": settings.APP_NAME,
            "version": settings.APP_VERSION,
            "environment": settings.APP_ENV.value,
        }

    @app.get(
        "/ready",
        tags=["System"],
        summary="Readiness check",
        response_class=ORJSONResponse,
    )
    async def readiness_check() -> dict:
        """
        Readiness probe for orchestrators (Kubernetes, ECS, etc.).
        Verifies that the application finished startup tasks.
        """
        checks: dict[str, str] = {
            "application": "ok",
            "filesystem": "ok" if settings.resolved_upload_dir.exists() else "down",
        }
        overall = "ready" if all(v == "ok" for v in checks.values()) else "degraded"
        return {
            "status": overall,
            "components": checks,
            "uptime_seconds": round(time.time() - _BOOT_TIMESTAMP, 2),
        }

    @app.get(
        "/version",
        tags=["System"],
        summary="Application version",
        response_class=ORJSONResponse,
    )
    async def version_info() -> dict:
        """Return structured version and build metadata."""
        return {
            "app": settings.APP_NAME,
            "version": settings.APP_VERSION,
            "environment": settings.APP_ENV.value,
            "debug": settings.APP_DEBUG,
        }


# ═══════════════════════════════════════════════════════════════════════════════
# Application Instance
# ═══════════════════════════════════════════════════════════════════════════════

app: FastAPI = create_application()
"""Module-level application instance — used by ``uvicorn backend.main:app``."""


# ═══════════════════════════════════════════════════════════════════════════════
# CLI Entrypoint
# ═══════════════════════════════════════════════════════════════════════════════

if __name__ == "__main__":
    import uvicorn

    uvicorn.run(
        "backend.main:app",
        host=settings.APP_HOST,
        port=settings.APP_PORT,
        workers=settings.APP_WORKERS,
        reload=settings.is_development,
        log_level=settings.LOG_LEVEL.lower(),
    )
