# ═══════════════════════════════════════════════════════════════════════════════
# Veloce Engine — Dashboard API Routes
# ═══════════════════════════════════════════════════════════════════════════════
"""
API v1 endpoints for the Dashboard Generator.

Endpoints:

* ``GET /api/v1/dashboards/{dataset_id}/generate`` — Auto-generate a dashboard layout.
"""

from __future__ import annotations

from fastapi import APIRouter
from fastapi.responses import ORJSONResponse

from backend.core.logging import get_logger
from backend.schemas.dashboard import DashboardResponse
from backend.services.dashboard_engine import get_dashboard_engine
from backend.services.dataframe_manager import get_dataframe_manager

_logger = get_logger(__name__)

router = APIRouter(
    prefix="/api/v1/dashboards",
    tags=["Dashboards"],
    default_response_class=ORJSONResponse,
)


# ═══════════════════════════════════════════════════════════════════════════════
# Generate Dashboard
# ═══════════════════════════════════════════════════════════════════════════════

@router.get(
    "/{dataset_id}/generate",
    response_model=DashboardResponse,
    summary="Auto-generate an analytical dashboard",
    description=(
        "Uses the Profiler and Correlation Engines to intelligently design a "
        "declarative dashboard layout (JSON) containing global filters, KPI cards, "
        "and optimized charts (line, bar, scatter, etc.)."
    ),
)
async def generate_dashboard(dataset_id: str) -> DashboardResponse:
    """
    Generate a declarative dashboard configuration for the dataset.
    """
    manager = get_dataframe_manager()
    engine = get_dashboard_engine()

    metadata = manager.get_dataset(dataset_id)
    df = manager.get_dataframe(dataset_id)

    layout = await engine.generate_dashboard(dataset_id, df, metadata.original_filename)

    return DashboardResponse(dashboard=layout)
