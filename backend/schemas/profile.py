# ═══════════════════════════════════════════════════════════════════════════════
# Veloce Engine — Dataset Profile Schemas
# ═══════════════════════════════════════════════════════════════════════════════
"""
Pydantic v2 response schemas for the Profiling Engine.

These models define the wire format for dataset and column profile data.
"""

from __future__ import annotations

import enum
from datetime import datetime
from typing import Any

from pydantic import BaseModel, Field


# ═══════════════════════════════════════════════════════════════════════════════
# Enums
# ═══════════════════════════════════════════════════════════════════════════════

class SemanticType(str, enum.Enum):
    """
    Semantic column type inferred from data characteristics.

    Goes beyond raw pandas dtypes to capture the analytical role of each
    column.
    """
    NUMERIC_INTEGER = "numeric_integer"
    NUMERIC_FLOAT = "numeric_float"
    CATEGORICAL = "categorical"
    BOOLEAN = "boolean"
    DATETIME = "datetime"
    TEXT = "text"
    IDENTIFIER = "identifier"
    UNKNOWN = "unknown"


class ColumnRole(str, enum.Enum):
    """
    Analytical role of a column — determines how the dashboard engine
    uses this column (axis, aggregation, filter, etc.).
    """
    DIMENSION = "dimension"
    MEASURE = "measure"
    TIME = "time"
    IDENTIFIER = "identifier"
    TEXT = "text"


# ═══════════════════════════════════════════════════════════════════════════════
# Per-Column Profile
# ═══════════════════════════════════════════════════════════════════════════════

class NumericStats(BaseModel):
    """Descriptive statistics for numeric columns."""
    mean: float | None = None
    median: float | None = None
    std: float | None = None
    min: float | None = None
    max: float | None = None
    q1: float | None = Field(default=None, description="25th percentile.")
    q3: float | None = Field(default=None, description="75th percentile.")
    iqr: float | None = Field(default=None, description="Interquartile range.")
    skewness: float | None = None
    kurtosis: float | None = None
    sum: float | None = None
    zeros_count: int = 0
    negative_count: int = 0
    positive_count: int = 0


class CategoricalStats(BaseModel):
    """Frequency statistics for categorical columns."""
    top_values: list[dict[str, Any]] = Field(
        default_factory=list,
        description="Most frequent values with counts: [{value, count, percentage}].",
    )
    unique_count: int = 0
    mode: str | None = None
    mode_frequency: int = 0


class OutlierInfo(BaseModel):
    """Outlier detection results for a numeric column."""
    method: str = "iqr"
    lower_bound: float | None = None
    upper_bound: float | None = None
    outlier_count: int = 0
    outlier_percentage: float = 0.0


class MissingValueInfo(BaseModel):
    """Missing value analysis for a column."""
    count: int = 0
    percentage: float = 0.0
    completeness: float = Field(
        default=100.0,
        description="Percentage of non-null values (0–100).",
    )


class ColumnProfile(BaseModel):
    """Comprehensive profile for a single column."""

    # ── Identity ─────────────────────────────────────────────────────
    name: str = Field(description="Column name.")
    position: int = Field(description="0-based column index.")

    # ── Type Information ─────────────────────────────────────────────
    pandas_dtype: str = Field(description="Raw pandas dtype string.")
    semantic_type: SemanticType = Field(description="Inferred semantic type.")
    role: ColumnRole = Field(description="Analytical role (dimension/measure/time).")

    # ── Cardinality ──────────────────────────────────────────────────
    total_count: int = Field(description="Total row count.")
    unique_count: int = Field(description="Number of unique values.")
    uniqueness_ratio: float = Field(
        description="unique_count / total_count (0.0–1.0).",
    )
    is_unique: bool = Field(description="True if every value is unique.")
    is_constant: bool = Field(description="True if only one distinct value.")

    # ── Missing Values ───────────────────────────────────────────────
    missing: MissingValueInfo = Field(default_factory=MissingValueInfo)

    # ── Statistics ───────────────────────────────────────────────────
    numeric_stats: NumericStats | None = None
    categorical_stats: CategoricalStats | None = None

    # ── Outliers ─────────────────────────────────────────────────────
    outliers: OutlierInfo | None = None

    # ── Sample Values ────────────────────────────────────────────────
    sample_values: list[Any] = Field(
        default_factory=list,
        description="Up to 5 sample non-null values.",
    )


# ═══════════════════════════════════════════════════════════════════════════════
# Dataset-Level Profile
# ═══════════════════════════════════════════════════════════════════════════════

class DatasetProfile(BaseModel):
    """Aggregate profile for an entire dataset."""

    dataset_id: str
    filename: str
    row_count: int
    column_count: int

    # ── Column Role Summary ──────────────────────────────────────────
    dimensions: list[str] = Field(
        default_factory=list,
        description="Column names classified as dimensions.",
    )
    measures: list[str] = Field(
        default_factory=list,
        description="Column names classified as measures.",
    )
    time_columns: list[str] = Field(
        default_factory=list,
        description="Column names classified as time fields.",
    )
    identifiers: list[str] = Field(
        default_factory=list,
        description="Column names classified as identifiers.",
    )

    # ── Data Quality Summary ─────────────────────────────────────────
    total_missing_cells: int = 0
    total_cells: int = 0
    overall_completeness: float = Field(
        default=100.0,
        description="Percentage of non-null cells across the dataset.",
    )

    # ── Memory ───────────────────────────────────────────────────────
    memory_usage_bytes: int = 0
    memory_usage_display: str = ""

    # ── Per-Column Profiles ──────────────────────────────────────────
    columns: list[ColumnProfile] = Field(default_factory=list)

    # ── Profiling Metadata ───────────────────────────────────────────
    profiled_at: datetime | None = None
    profiling_duration_ms: float = 0.0


# ═══════════════════════════════════════════════════════════════════════════════
# API Response Wrapper
# ═══════════════════════════════════════════════════════════════════════════════

class ProfileResponse(BaseModel):
    """API response wrapper for dataset profiling."""
    status: str = "success"
    profile: DatasetProfile
