# ═══════════════════════════════════════════════════════════════════════════════
# Veloce Engine — Dashboard Generator Schemas
# ═══════════════════════════════════════════════════════════════════════════════
"""
Pydantic v2 schemas for the automated Dashboard Generator.

These models define the declarative JSON payload that instructs the frontend
on how to render an entire AI-generated dashboard (filters, KPIs, charts).
"""

from __future__ import annotations

import enum

from pydantic import BaseModel, Field


# ═══════════════════════════════════════════════════════════════════════════════
# Enums
# ═══════════════════════════════════════════════════════════════════════════════

class ChartType(str, enum.Enum):
    """Supported frontend chart types."""
    BAR = "bar"
    LINE = "line"
    SCATTER = "scatter"
    PIE = "pie"
    DONUT = "donut"
    TABLE = "table"


class FilterType(str, enum.Enum):
    """Supported frontend filter UI components."""
    DROPDOWN = "dropdown"
    MULTI_SELECT = "multi_select"
    DATE_RANGE = "date_range"
    SLIDER = "slider"


# ═══════════════════════════════════════════════════════════════════════════════
# Dashboard Components
# ═══════════════════════════════════════════════════════════════════════════════

class DashboardFilter(BaseModel):
    """A global filter for the dashboard."""
    column: str = Field(description="The column to filter on.")
    filter_type: FilterType = Field(description="The UI component to render.")
    label: str = Field(description="Human-readable label for the filter.")


class KpiCard(BaseModel):
    """A top-level KPI metric card."""
    id: str
    title: str = Field(description="Title of the KPI (e.g., 'Total Sales').")
    measure_column: str = Field(description="The numeric column to aggregate.")
    aggregation: str = Field(description="Aggregation function (e.g., 'sum', 'mean').")
    format_as: str = Field(default="number", description="'number', 'currency', or 'percent'.")
    trend_column: str | None = Field(default=None, description="Time column for trend lines, if any.")


class ChartConfig(BaseModel):
    """Configuration for a specific chart."""
    id: str
    title: str = Field(description="Chart title.")
    chart_type: ChartType
    x_axis: str | None = Field(default=None, description="Column for the X-axis (Dimension).")
    y_axis: list[str] = Field(default_factory=list, description="Columns for the Y-axis (Measures).")
    group_by: str | None = Field(default=None, description="Column for color/series grouping.")
    aggregation: str = Field(default="sum", description="Aggregation function for the Y-axis.")
    description: str | None = Field(default=None, description="AI-generated subtext explaining the chart.")


# ═══════════════════════════════════════════════════════════════════════════════
# Payload Models
# ═══════════════════════════════════════════════════════════════════════════════

class DashboardLayout(BaseModel):
    """The complete, AI-generated dashboard definition."""
    dataset_id: str
    title: str = Field(description="Overall dashboard title.")
    filters: list[DashboardFilter] = Field(default_factory=list)
    kpi_cards: list[KpiCard] = Field(default_factory=list)
    charts: list[ChartConfig] = Field(default_factory=list)


class DashboardResponse(BaseModel):
    """API response wrapper for dashboard generation."""
    status: str = "success"
    message: str = "Dashboard generated successfully."
    dashboard: DashboardLayout
