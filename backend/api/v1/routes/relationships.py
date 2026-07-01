# ═══════════════════════════════════════════════════════════════════════════════
# Veloce Engine — Relationship API Routes
# ═══════════════════════════════════════════════════════════════════════════════
"""
API v1 endpoints for Relationship Discovery Engine.

Endpoints:

* ``GET  /api/v1/relationships/single/{dataset_id}`` — Analyze relationships within one dataset.
* ``POST /api/v1/relationships/graph``                — Build relationship graph across multiple datasets.
"""

from __future__ import annotations

from fastapi import APIRouter
from fastapi.responses import ORJSONResponse
from pydantic import BaseModel, Field

from backend.core.logging import get_logger
from backend.schemas.relationship import (
    MultiDatasetRelationshipResponse,
    SingleDatasetRelationshipResponse,
)
from backend.services.relationship_engine import get_relationship_engine
from backend.services.dataframe_manager import get_dataframe_manager

_logger = get_logger(__name__)

router = APIRouter(
    prefix="/api/v1/relationships",
    tags=["Relationships"],
    default_response_class=ORJSONResponse,
)


class GraphRequest(BaseModel):
    """Request payload to specify which datasets to include in the graph."""
    dataset_ids: list[str] | None = Field(
        default=None,
        description="List of dataset IDs to analyze. If omitted, analyzes all datasets.",
    )


# ═══════════════════════════════════════════════════════════════════════════════
# Single Dataset Analysis
# ═══════════════════════════════════════════════════════════════════════════════

@router.get(
    "/single/{dataset_id}",
    response_model=SingleDatasetRelationshipResponse,
    summary="Analyze relationships within a single dataset",
    description=(
        "Analyzes a single dataset to automatically discover primary key candidates, "
        "numeric correlations, and functional dependencies."
    ),
)
async def analyze_single_dataset(dataset_id: str) -> SingleDatasetRelationshipResponse:
    manager = get_dataframe_manager()
    engine = get_relationship_engine()

    df = manager.get_dataframe(dataset_id)

    relationships = await engine.analyze_single_dataset(dataset_id, df)

    return SingleDatasetRelationshipResponse(relationships=relationships)


# ═══════════════════════════════════════════════════════════════════════════════
# Multi-Dataset Graph Analysis
# ═══════════════════════════════════════════════════════════════════════════════

@router.post(
    "/graph",
    response_model=MultiDatasetRelationshipResponse,
    summary="Build relationship graph across datasets",
    description=(
        "Discovers relationships (like foreign keys and join paths) across multiple "
        "datasets. Supports automated detection of 1:1, 1:N, N:1, and M:N cardinality."
    ),
)
async def build_relationship_graph(request: GraphRequest) -> MultiDatasetRelationshipResponse:
    manager = get_dataframe_manager()
    engine = get_relationship_engine()

    # Determine which datasets to load
    target_ids = request.dataset_ids
    if not target_ids:
        # Load all datasets if none specified
        all_meta = manager.list_datasets()
        target_ids = [m.dataset_id for m in all_meta]

    _logger.info("building_graph_for_datasets", count=len(target_ids))

    datasets = {ds_id: manager.get_dataframe(ds_id) for ds_id in target_ids}

    # Build Graph
    graph = await engine.build_relationship_graph(datasets)

    return MultiDatasetRelationshipResponse(graph=graph)
