# ═══════════════════════════════════════════════════════════════════════════════
# Veloce Engine — Insight API Routes
# ═══════════════════════════════════════════════════════════════════════════════
"""
API v1 endpoints for the AI Insight Engine.

Endpoints:

* ``GET /api/v1/insights/{dataset_id}`` — Auto-generate natural language insights.
"""

from __future__ import annotations

from fastapi import APIRouter
from fastapi.responses import ORJSONResponse

from backend.core.logging import get_logger
from backend.schemas.insights import InsightsResponse
from backend.services.insight_engine import get_insight_engine
from backend.services.dataframe_manager import get_dataframe_manager

_logger = get_logger(__name__)

router = APIRouter(
    prefix="/api/v1/insights",
    tags=["Insights"],
    default_response_class=ORJSONResponse,
)


# ═══════════════════════════════════════════════════════════════════════════════
# Generate Insights
# ═══════════════════════════════════════════════════════════════════════════════

@router.get(
    "/{dataset_id}",
    response_model=InsightsResponse,
    summary="Auto-generate Natural Language Insights",
    description=(
        "Uses the Profiler, Semantic, and Correlation Engines to intelligently "
        "synthesize human-readable observations about data quality, trends, "
        "correlations, and distributions."
    ),
)
async def generate_insights(dataset_id: str) -> InsightsResponse:
    """
    Generate an array of NLP insights for the dataset.
    """
    manager = get_dataframe_manager()
    engine = get_insight_engine()

    metadata = manager.get_dataset(dataset_id)
    df = manager.get_dataframe(dataset_id)

    response = await engine.generate_insights(dataset_id, df, metadata.original_filename)

    return response
