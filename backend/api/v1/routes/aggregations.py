# ═══════════════════════════════════════════════════════════════════════════════
# Veloce Engine — Aggregation API Routes
# ═══════════════════════════════════════════════════════════════════════════════
"""
API v1 endpoints for the Aggregation Engine.

Endpoints:

* ``POST /api/v1/aggregations/{dataset_id}`` — Execute a dynamic query.
"""

from __future__ import annotations

from fastapi import APIRouter
from fastapi.responses import ORJSONResponse

from backend.core.logging import get_logger
from backend.schemas.aggregation import QueryRequest, QueryResponse
from backend.services.aggregation_engine import get_aggregation_engine
from backend.services.dataframe_manager import get_dataframe_manager

_logger = get_logger(__name__)

router = APIRouter(
    prefix="/api/v1/aggregations",
    tags=["Aggregations"],
    default_response_class=ORJSONResponse,
)


# ═══════════════════════════════════════════════════════════════════════════════
# Query Execution
# ═══════════════════════════════════════════════════════════════════════════════

@router.post(
    "/{dataset_id}",
    response_model=QueryResponse,
    summary="Execute dynamic aggregation query",
    description=(
        "Executes a declarative JSON query payload. Supports row-level filtering, "
        "dimension grouping, measure aggregation (sum, mean, etc.), sorting, "
        "and pagination."
    ),
)
async def execute_aggregation_query(
    dataset_id: str,
    query: QueryRequest,
) -> QueryResponse:
    """
    Run a dynamic data query.
    """
    manager = get_dataframe_manager()
    engine = get_aggregation_engine()

    df = manager.get_dataframe(dataset_id)

    response = await engine.execute_query(dataset_id, df, query)

    return response
