# ═══════════════════════════════════════════════════════════════════════════════
# Veloce Engine — Semantic API Routes
# ═══════════════════════════════════════════════════════════════════════════════
"""
API v1 endpoints for the Semantic AI Layer.

Endpoints:

* ``GET /api/v1/semantics/{dataset_id}`` — Analyze a dataset for business entities.
"""

from __future__ import annotations

from fastapi import APIRouter
from fastapi.responses import ORJSONResponse

from backend.core.logging import get_logger
from backend.schemas.semantic import SemanticAnalysisResponse
from backend.services.semantic_engine import get_semantic_engine
from backend.services.dataframe_manager import get_dataframe_manager

_logger = get_logger(__name__)

router = APIRouter(
    prefix="/api/v1/semantics",
    tags=["Semantics"],
    default_response_class=ORJSONResponse,
)


# ═══════════════════════════════════════════════════════════════════════════════
# Semantic Analysis
# ═══════════════════════════════════════════════════════════════════════════════

@router.get(
    "/{dataset_id}",
    response_model=SemanticAnalysisResponse,
    summary="Semantic AI analysis of a dataset",
    description=(
        "Analyzes a dataset to automatically discover the business meaning "
        "(e.g., Email, Phone Number, Currency) of each column using a combination "
        "of name heuristics and regex-based data sampling."
    ),
)
async def analyze_dataset_semantics(dataset_id: str) -> SemanticAnalysisResponse:
    """
    Generate a semantic profile for the dataset.
    """
    manager = get_dataframe_manager()
    engine = get_semantic_engine()

    df = manager.get_dataframe(dataset_id)

    _logger.info("semantic_analysis_requested", dataset_id=dataset_id)

    semantics = await engine.analyze_dataset(dataset_id, df)

    return SemanticAnalysisResponse(semantics=semantics)
