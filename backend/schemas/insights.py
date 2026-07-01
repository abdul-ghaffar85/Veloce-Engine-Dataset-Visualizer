# ═══════════════════════════════════════════════════════════════════════════════
# Veloce Engine — AI Insight Schemas
# ═══════════════════════════════════════════════════════════════════════════════
"""
Pydantic v2 schemas for the AI Insight Engine.

These models define the structure of natural-language insights generated
automatically from statistical dataset properties.
"""

from __future__ import annotations

import enum

from pydantic import BaseModel, Field


# ═══════════════════════════════════════════════════════════════════════════════
# Enums
# ═══════════════════════════════════════════════════════════════════════════════

class InsightType(str, enum.Enum):
    """The category of the generated insight."""
    TREND = "trend"
    CORRELATION = "correlation"
    DATA_QUALITY = "data_quality"
    DISTRIBUTION = "distribution"
    SEMANTIC = "semantic"


class InsightSeverity(str, enum.Enum):
    """The severity or tone of the insight."""
    INFO = "info"          # General interesting fact
    WARNING = "warning"    # Potential data issue or negative trend
    CRITICAL = "critical"  # Severe data quality issue
    SUCCESS = "success"    # Positive trend or exceptionally clean data


# ═══════════════════════════════════════════════════════════════════════════════
# Insight Models
# ═══════════════════════════════════════════════════════════════════════════════

class Insight(BaseModel):
    """A single natural-language insight."""
    insight_type: InsightType
    severity: InsightSeverity
    title: str = Field(description="Short summary (e.g., 'Strong Positive Correlation').")
    description: str = Field(description="Detailed natural language explanation.")
    related_columns: list[str] = Field(
        default_factory=list,
        description="Columns involved in this insight to allow UI cross-filtering."
    )


class InsightsResponse(BaseModel):
    """API response wrapper for dataset insights."""
    status: str = "success"
    dataset_id: str
    insights: list[Insight] = Field(
        description="A list of human-readable insights sorted by priority/severity."
    )
