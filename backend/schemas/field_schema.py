# ═══════════════════════════════════════════════════════════════════════════════
# Veloce Engine — Field Schema (XLBooster-Style Semantic Metadata)
# ═══════════════════════════════════════════════════════════════════════════════
"""
Pydantic v2 schemas for the Semantic Field Schema Engine.

These models define the wire format for the interactive drag-and-drop
analytics interface.  Each column in a dataset is described by a
``FieldDescriptor`` that combines profiling, semantic analysis, and
aggregation suggestions into a single structure.

The frontend uses these descriptors to populate the Dimensions and
Metrics sidebars, and to validate user-constructed chart configurations.
"""

from __future__ import annotations

import enum
from typing import Any

from pydantic import BaseModel, Field
from pydantic import ConfigDict


# ═══════════════════════════════════════════════════════════════════════════════
# Enums
# ═══════════════════════════════════════════════════════════════════════════════

class FieldSemanticType(str, enum.Enum):
    """High-level analytical classification for a column."""
    DIMENSION = "dimension"
    METRIC = "metric"
    TIME = "time"
    IDENTIFIER = "identifier"
    TEXT = "text"


class FieldDataType(str, enum.Enum):
    """Simplified data type for frontend consumption."""
    STRING = "string"
    INTEGER = "integer"
    FLOAT = "float"
    BOOLEAN = "boolean"
    DATETIME = "datetime"


# ═══════════════════════════════════════════════════════════════════════════════
# Field Statistics (lightweight summary for sidebar tooltips)
# ═══════════════════════════════════════════════════════════════════════════════

class FieldStatistics(BaseModel):
    """Compact statistics summary embedded in each field descriptor."""

    # Numeric metrics
    min: float | None = None
    max: float | None = None
    mean: float | None = None
    median: float | None = None
    sum: float | None = None
    std: float | None = None

    # Categorical / general
    mode: str | None = None
    top_values: list[dict[str, Any]] = Field(
        default_factory=list,
        description="Top 10 values with counts: [{value, count, percentage}].",
    )

    # Missing
    missing_count: int = 0
    missing_percentage: float = 0.0
    completeness: float = 100.0

    # Outliers (numeric only)
    outlier_count: int = 0
    outlier_percentage: float = 0.0


# ═══════════════════════════════════════════════════════════════════════════════
# Field Descriptor — The Core Unit
# ═══════════════════════════════════════════════════════════════════════════════

class FieldDescriptor(BaseModel):
    """
    Complete metadata for a single column, optimised for a drag-and-drop
    analytics interface.

    Combines profiling results, semantic entity recognition, aggregation
    suggestions, and sample values into one structure.
    """

    # ── Identity ─────────────────────────────────────────────────────
    field: str = Field(description="Column name.")
    position: int = Field(description="0-based column index.")

    # ── Classification ───────────────────────────────────────────────
    semanticType: FieldSemanticType = Field(
        description="Analytical role: dimension, metric, time, identifier, text.",
    )
    dataType: FieldDataType = Field(
        description="Simplified data type for the frontend.",
    )
    businessEntity: str | None = Field(
        default=None,
        description=(
            "Business-level entity (e.g., 'email', 'currency', 'country'). "
            "Null if no entity could be inferred."
        ),
    )

    # ── Cardinality ──────────────────────────────────────────────────
    nullable: bool = Field(description="True if the column has null values.")
    cardinality: int = Field(description="Number of unique non-null values.")
    uniquenessRatio: float = Field(
        description="Ratio of unique values to total rows (0.0–1.0).",
    )
    isUnique: bool = Field(description="True if every value is unique.")
    isConstant: bool = Field(description="True if only one distinct value.")

    # ── Aggregation ──────────────────────────────────────────────────
    aggregations: list[str] = Field(
        default_factory=list,
        description=(
            "Suggested aggregation functions using Pandas-compatible names "
            "(e.g., 'sum', 'mean', 'count', 'nunique', 'min', 'max')."
        ),
    )
    defaultAggregation: str | None = Field(
        default=None,
        description="Recommended default aggregation for this field.",
    )

    # ── Sample Values ────────────────────────────────────────────────
    sampleValues: list[Any] = Field(
        default_factory=list,
        description="Up to 5 representative non-null values.",
    )
    uniqueValues: list[Any] | None = Field(
        default=None,
        description=(
            "All unique values for low-cardinality dimensions (≤50 unique). "
            "Null for high-cardinality fields."
        ),
    )

    # ── Date Hierarchy (time fields only) ────────────────────────────
    dateHierarchy: list[str] | None = Field(
        default=None,
        description=(
            "Available date granularities for time fields "
            "(e.g., ['year', 'quarter', 'month', 'week', 'day'])."
        ),
    )

    # ── Numeric Precision (float fields only) ────────────────────────
    numericPrecision: int | None = Field(
        default=None,
        description="Number of decimal places for float fields.",
    )

    # ── Statistics ───────────────────────────────────────────────────
    statistics: FieldStatistics = Field(
        default_factory=FieldStatistics,
        description="Compact statistics summary.",
    )


# ═══════════════════════════════════════════════════════════════════════════════
# Dataset-Level Response Models
# ═══════════════════════════════════════════════════════════════════════════════

class DatasetFieldSchema(BaseModel):
    """Complete field schema for an entire dataset."""

    dataset_id: str
    filename: str
    row_count: int
    column_count: int
    fields: list[FieldDescriptor] = Field(default_factory=list)
    dimension_count: int = 0
    metric_count: int = 0
    time_count: int = 0


class FieldSchemaResponse(BaseModel):
    """API response wrapper for the full field schema."""
    model_config = ConfigDict(populate_by_name=True)

    status: str = "success"
    field_schema: DatasetFieldSchema = Field(alias="schema")


class DimensionListResponse(BaseModel):
    """API response returning only dimension and time fields."""
    status: str = "success"
    dataset_id: str
    dimensions: list[FieldDescriptor] = Field(default_factory=list)
    count: int = 0


class MetricListResponse(BaseModel):
    """API response returning only metric fields."""
    status: str = "success"
    dataset_id: str
    metrics: list[FieldDescriptor] = Field(default_factory=list)
    count: int = 0


class DatasetMetadataResponse(BaseModel):
    """Combined metadata overview for a dataset."""
    status: str = "success"
    dataset_id: str
    filename: str
    row_count: int
    column_count: int
    dimension_count: int
    metric_count: int
    time_count: int
    identifier_count: int
    dimensions: list[str] = Field(default_factory=list)
    metrics: list[str] = Field(default_factory=list)
    time_fields: list[str] = Field(default_factory=list)
    identifiers: list[str] = Field(default_factory=list)
    overall_completeness: float = 100.0
    memory_usage_display: str = ""
