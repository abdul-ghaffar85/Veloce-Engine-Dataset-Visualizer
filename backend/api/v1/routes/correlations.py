# ═══════════════════════════════════════════════════════════════════════════════
# Veloce Engine — Correlation API Routes
# ═══════════════════════════════════════════════════════════════════════════════
"""
API v1 endpoints for the Correlation & Trend Engine.

Endpoints:

* ``GET /api/v1/correlations/{dataset_id}/matrix`` — Full numeric correlation matrix.
* ``GET /api/v1/correlations/{dataset_id}/importance/{target_column}`` — Feature importance.
* ``GET /api/v1/correlations/{dataset_id}/trends`` — Time-series trends for measures.
"""

from __future__ import annotations

from fastapi import APIRouter, Query
from fastapi.responses import ORJSONResponse

from backend.core.logging import get_logger
from backend.schemas.correlation import (
    CorrelationMatrixResponse,
    FeatureImportanceResponse,
    TrendAnalysisResponse,
)
from backend.services.correlation_engine import get_correlation_engine
from backend.services.dataframe_manager import get_dataframe_manager

_logger = get_logger(__name__)

router = APIRouter(
    prefix="/api/v1/correlations",
    tags=["Correlations"],
    default_response_class=ORJSONResponse,
)


# ═══════════════════════════════════════════════════════════════════════════════
# Correlation Matrix
# ═══════════════════════════════════════════════════════════════════════════════

@router.get(
    "/{dataset_id}/matrix",
    response_model=CorrelationMatrixResponse,
    summary="Get full numeric correlation matrix",
    description="Calculates Pearson and Spearman correlations between all numeric columns.",
)
async def get_correlation_matrix(dataset_id: str) -> CorrelationMatrixResponse:
    manager = get_dataframe_manager()
    engine = get_correlation_engine()

    df = manager.get_dataframe(dataset_id)

    return await engine.get_correlation_matrix(dataset_id, df)


# ═══════════════════════════════════════════════════════════════════════════════
# Feature Importance
# ═══════════════════════════════════════════════════════════════════════════════

@router.get(
    "/{dataset_id}/importance/{target_column}",
    response_model=FeatureImportanceResponse,
    summary="Calculate feature importance for a target",
    description=(
        "Ranks all other columns by their predictive correlation to the "
        "specified target column using Pearson or ANOVA Eta-Squared methods."
    ),
)
async def get_feature_importance(
    dataset_id: str,
    target_column: str,
) -> FeatureImportanceResponse:
    manager = get_dataframe_manager()
    engine = get_correlation_engine()

    df = manager.get_dataframe(dataset_id)

    return await engine.get_feature_importance(dataset_id, df, target_column)


# ═══════════════════════════════════════════════════════════════════════════════
# Time-Series Trends
# ═══════════════════════════════════════════════════════════════════════════════

@router.get(
    "/{dataset_id}/trends",
    response_model=TrendAnalysisResponse,
    summary="Analyze time-series trends",
    description=(
        "Calculates linear regression trends (slope, % change) for all numeric "
        "measures over time. If a time_column is not provided, the engine will "
        "attempt to auto-detect one."
    ),
)
async def get_trends(
    dataset_id: str,
    time_column: str | None = Query(
        default=None,
        description="Explicit column name to use for the X-axis time variable.",
    ),
) -> TrendAnalysisResponse:
    manager = get_dataframe_manager()
    engine = get_correlation_engine()

    df = manager.get_dataframe(dataset_id)

    return await engine.analyze_trends(dataset_id, df, time_column)
