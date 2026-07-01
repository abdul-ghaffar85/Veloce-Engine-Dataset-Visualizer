# ═══════════════════════════════════════════════════════════════════════════════
# Veloce Engine — Aggregation Engine Schemas
# ═══════════════════════════════════════════════════════════════════════════════
"""
Pydantic v2 schemas for the Aggregation Engine.

These models define the declarative JSON querying syntax used by the frontend
to filter, group, aggregate, sort, and paginate dataset records dynamically.
"""

from __future__ import annotations

import enum
from typing import Any

from pydantic import BaseModel, Field, model_validator


# ═══════════════════════════════════════════════════════════════════════════════
# Enums
# ═══════════════════════════════════════════════════════════════════════════════

class FilterOperator(str, enum.Enum):
    """Supported operations for filtering rows."""
    EQ = "eq"                  # Equal
    NEQ = "neq"                # Not equal
    GT = "gt"                  # Greater than
    GTE = "gte"                # Greater than or equal
    LT = "lt"                  # Less than
    LTE = "lte"                # Less than or equal
    CONTAINS = "contains"      # String contains (case-insensitive)
    IN = "in"                  # Value is in list
    NOT_IN = "not_in"          # Value is not in list
    IS_NULL = "is_null"        # Value is missing
    NOT_NULL = "not_null"      # Value is present


class AggregationFunction(str, enum.Enum):
    """Supported aggregation functions."""
    SUM = "sum"
    MEAN = "mean"
    MEDIAN = "median"
    COUNT = "count"            # Count non-null values
    UNIQUE_COUNT = "nunique"   # Count distinct values
    MIN = "min"
    MAX = "max"
    FIRST = "first"
    LAST = "last"


class SortOrder(str, enum.Enum):
    """Sort direction."""
    ASC = "asc"
    DESC = "desc"


# ═══════════════════════════════════════════════════════════════════════════════
# Query Components
# ═══════════════════════════════════════════════════════════════════════════════

class FilterCondition(BaseModel):
    """A single filter condition applied to a specific column."""
    column: str = Field(description="Column to filter by.")
    operator: FilterOperator = Field(description="Comparison operator.")
    value: Any = Field(default=None, description="Value to compare against. Omitted for is_null/not_null.")


class AggregateMetric(BaseModel):
    """An aggregation applied to a specific measure column."""
    column: str = Field(description="Column to aggregate (usually a measure).")
    function: AggregationFunction = Field(description="Mathematical function to apply.")
    alias: str | None = Field(default=None, description="Custom name for the output column.")


class SortCondition(BaseModel):
    """A sort instruction for a specific column."""
    column: str = Field(description="Column to sort by. Can be an original column or an aggregation alias.")
    order: SortOrder = Field(default=SortOrder.ASC, description="Ascending or Descending.")


# ═══════════════════════════════════════════════════════════════════════════════
# Payload Models
# ═══════════════════════════════════════════════════════════════════════════════

class QueryRequest(BaseModel):
    """
    Declarative query payload for dataset aggregation.
    
    Processed in order:
    1. Filter
    2. Group By & Aggregate
    3. Sort
    4. Paginate
    """
    filters: list[FilterCondition] = Field(default_factory=list, description="Row-level filters to apply first.")
    group_by: list[str] = Field(default_factory=list, description="Dimensions to group by.")
    aggregates: list[AggregateMetric] = Field(default_factory=list, description="Metrics to calculate.")
    sort: list[SortCondition] = Field(default_factory=list, description="Sorting rules applied to the final result set.")
    limit: int = Field(default=100, ge=1, le=10000, description="Max rows to return.")
    offset: int = Field(default=0, ge=0, description="Rows to skip (for pagination).")
    # UI-specific properties transmitted for tracking/validation
    chartType: str | None = Field(default=None, description="Chart type chosen by the user.")
    xAxis: str | None = Field(default=None, description="Selected dimension for X Axis.")
    yAxis: str | None = Field(default=None, description="Selected measure for Y Axis.")
    aggregation: str | None = Field(default=None, description="Selected aggregation for Y Axis.")

    @model_validator(mode='after')
    def validate_chart_requirements(self) -> QueryRequest:
        """Reject invalid chart requests with HTTP 422."""
        if self.chartType is not None:
            # KPI/Metric only needs yAxis
            if self.chartType in ['kpi', 'metric']:
                if self.yAxis is None:
                    raise ValueError(f"chartType '{self.chartType}' requires yAxis to be specified")
            # Other charts need both xAxis and yAxis
            else:
                if self.xAxis is None or self.yAxis is None:
                    raise ValueError(f"chartType '{self.chartType}' requires both xAxis and yAxis to be specified")
        return self


class QueryResponse(BaseModel):
    """Results of a dynamic query execution."""
    status: str = "success"
    dataset_id: str
    total_rows: int = Field(description="Total rows matched by filters (before grouping/pagination).")
    returned_rows: int = Field(description="Number of rows in the current payload.")
    data: list[dict[str, Any]] = Field(description="The actual data rows.")
    execution_time_ms: float = Field(description="Query execution time in milliseconds.")
