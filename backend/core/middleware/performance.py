# ═══════════════════════════════════════════════════════════════════════════════
# Veloce Engine — Performance Middleware
# ═══════════════════════════════════════════════════════════════════════════════
"""
Middleware for tracking request duration and emitting structured logs for
monitoring and performance analytics.
"""

from __future__ import annotations

import time

from fastapi import Request
from starlette.middleware.base import BaseHTTPMiddleware, RequestResponseEndpoint
from starlette.responses import Response

from backend.core.logging import get_logger

_logger = get_logger("veloce.monitoring")


class PerformanceMetricsMiddleware(BaseHTTPMiddleware):
    """
    Measures and logs request latency.
    
    Emits structured JSON logs containing:
    - method: HTTP method
    - path: Request path
    - duration_ms: Total execution time in milliseconds
    - status_code: HTTP response status
    """

    async def dispatch(
        self, request: Request, call_next: RequestResponseEndpoint
    ) -> Response:
        start_time = time.perf_counter()

        try:
            response = await call_next(request)
            status_code = response.status_code
            return response
        except Exception:
            status_code = 500
            raise
        finally:
            process_time_ms = (time.perf_counter() - start_time) * 1000

            # Only log API endpoints, ignore static files or root
            if request.url.path.startswith("/api/") or request.url.path in ("/health", "/ready"):
                _logger.info(
                    "http_request_performance",
                    method=request.method,
                    path=request.url.path,
                    duration_ms=round(process_time_ms, 2),
                    status_code=status_code,
                    client_ip=request.client.host if request.client else "unknown",
                )
