# ═══════════════════════════════════════════════════════════════════════════════
# Veloce Engine — Field Schema API Routes
# ═══════════════════════════════════════════════════════════════════════════════
"""
API v1 endpoints for the XLBooster-style Semantic Field Schema.

These endpoints expose structured metadata about every column in a dataset,
classified into dimensions, metrics, and time fields with aggregation
suggestions — the foundation for the interactive drag-and-drop UI.

Endpoints:

* ``GET /api/v1/datasets/{dataset_id}/schema``      — Full field schema.
* ``GET /api/v1/datasets/{dataset_id}/dimensions``   — Dimension fields only.
* ``GET /api/v1/datasets/{dataset_id}/metrics``      — Metric fields only.
* ``GET /api/v1/datasets/{dataset_id}/metadata``     — Summary metadata overview.
"""

from __future__ import annotations

from fastapi import APIRouter
from fastapi.responses import ORJSONResponse

from backend.core.logging import get_logger
from backend.schemas.field_schema import (
    DatasetMetadataResponse,
    DimensionListResponse,
    FieldSchemaResponse,
    FieldSemanticType,
    MetricListResponse,
)
from backend.services.dataframe_manager import get_dataframe_manager
from backend.services.field_schema_engine import get_field_schema_engine

_logger = get_logger(__name__)

router = APIRouter(
    prefix="/api/v1/datasets",
    tags=["Field Schema"],
    default_response_class=ORJSONResponse,
)


# ═══════════════════════════════════════════════════════════════════════════════
# Full Field Schema
# ═══════════════════════════════════════════════════════════════════════════════

@router.get(
    "/{dataset_id}/schema",
    response_model=FieldSchemaResponse,
    summary="Get full field schema",
    description=(
        "Returns the complete semantic field schema for a dataset. "
        "Every column is classified as a dimension, metric, time, or "
        "identifier with suggested aggregations, data types, cardinality, "
        "and sample values."
    ),
)
async def get_field_schema(dataset_id: str) -> FieldSchemaResponse:
    """
    Build and return the field schema for a dataset.

    This endpoint runs the full profiling + semantic analysis pipeline
    and merges the results into a unified field descriptor format.
    """
    manager = get_dataframe_manager()
    engine = get_field_schema_engine()

    metadata = manager.get_dataset(dataset_id)
    df = manager.get_dataframe(dataset_id)

    _logger.info(
        "field_schema_requested",
        dataset_id=dataset_id,
        rows=len(df),
        columns=len(df.columns),
    )

    schema = await engine.build_schema(
        dataset_id=dataset_id,
        filename=metadata.original_filename,
        df=df,
    )

    return FieldSchemaResponse(field_schema=schema)


# ═══════════════════════════════════════════════════════════════════════════════
# Dimensions Only
# ═══════════════════════════════════════════════════════════════════════════════

@router.get(
    "/{dataset_id}/dimensions",
    response_model=DimensionListResponse,
    summary="Get dimension fields",
    description=(
        "Returns only the fields classified as dimensions or time fields. "
        "These are the fields users can drag into the X-axis, Color, "
        "Filters, and other categorical slots."
    ),
)
async def get_dimensions(dataset_id: str) -> DimensionListResponse:
    """Return dimension and time fields for the dataset."""
    manager = get_dataframe_manager()
    engine = get_field_schema_engine()

    metadata = manager.get_dataset(dataset_id)
    df = manager.get_dataframe(dataset_id)

    schema = await engine.build_schema(
        dataset_id=dataset_id,
        filename=metadata.original_filename,
        df=df,
    )

    dimensions = [
        f for f in schema.fields
        if f.semanticType in (
            FieldSemanticType.DIMENSION,
            FieldSemanticType.TIME,
            FieldSemanticType.TEXT,
        )
    ]

    return DimensionListResponse(
        dataset_id=dataset_id,
        dimensions=dimensions,
        count=len(dimensions),
    )


# ═══════════════════════════════════════════════════════════════════════════════
# Metrics Only
# ═══════════════════════════════════════════════════════════════════════════════

@router.get(
    "/{dataset_id}/metrics",
    response_model=MetricListResponse,
    summary="Get metric fields",
    description=(
        "Returns only the fields classified as metrics (measures). "
        "These are the numeric fields users can drag into Y-axis, "
        "Size, and other aggregation slots."
    ),
)
async def get_metrics(dataset_id: str) -> MetricListResponse:
    """Return metric (measure) fields for the dataset."""
    manager = get_dataframe_manager()
    engine = get_field_schema_engine()

    metadata = manager.get_dataset(dataset_id)
    df = manager.get_dataframe(dataset_id)

    schema = await engine.build_schema(
        dataset_id=dataset_id,
        filename=metadata.original_filename,
        df=df,
    )

    metrics = [
        f for f in schema.fields
        if f.semanticType == FieldSemanticType.METRIC
    ]

    return MetricListResponse(
        dataset_id=dataset_id,
        metrics=metrics,
        count=len(metrics),
    )


# ═══════════════════════════════════════════════════════════════════════════════
# Combined Metadata Overview
# ═══════════════════════════════════════════════════════════════════════════════

@router.get(
    "/{dataset_id}/metadata",
    response_model=DatasetMetadataResponse,
    summary="Get dataset metadata overview",
    description=(
        "Returns a lightweight metadata summary: field counts by type, "
        "lists of dimension/metric/time column names, data quality stats."
    ),
)
async def get_dataset_metadata(dataset_id: str) -> DatasetMetadataResponse:
    """Return a metadata overview for the dataset."""
    manager = get_dataframe_manager()
    engine = get_field_schema_engine()

    metadata = manager.get_dataset(dataset_id)
    df = manager.get_dataframe(dataset_id)

    schema = await engine.build_schema(
        dataset_id=dataset_id,
        filename=metadata.original_filename,
        df=df,
    )

    dimensions = [
        f.field for f in schema.fields
        if f.semanticType in (FieldSemanticType.DIMENSION, FieldSemanticType.TEXT)
    ]
    metrics = [
        f.field for f in schema.fields
        if f.semanticType == FieldSemanticType.METRIC
    ]
    time_fields = [
        f.field for f in schema.fields
        if f.semanticType == FieldSemanticType.TIME
    ]
    identifiers = [
        f.field for f in schema.fields
        if f.semanticType == FieldSemanticType.IDENTIFIER
    ]

    # Calculate overall completeness
    total_missing = sum(f.statistics.missing_count for f in schema.fields)
    total_cells = schema.row_count * schema.column_count
    completeness = (
        ((total_cells - total_missing) / total_cells * 100)
        if total_cells > 0
        else 100.0
    )

    # Memory usage
    mem_bytes = int(df.memory_usage(deep=True).sum())
    mem_display = _format_bytes(mem_bytes)

    return DatasetMetadataResponse(
        dataset_id=dataset_id,
        filename=metadata.original_filename,
        row_count=schema.row_count,
        column_count=schema.column_count,
        dimension_count=len(dimensions),
        metric_count=len(metrics),
        time_count=len(time_fields),
        identifier_count=len(identifiers),
        dimensions=dimensions,
        metrics=metrics,
        time_fields=time_fields,
        identifiers=identifiers,
        overall_completeness=round(completeness, 2),
        memory_usage_display=mem_display,
    )


def _format_bytes(size: int) -> str:
    """Convert bytes to human-readable string."""
    for unit in ("B", "KB", "MB", "GB"):
        if abs(size) < 1024:
            return f"{size:.1f} {unit}"
        size /= 1024  # type: ignore[assignment]
    return f"{size:.1f} TB"
