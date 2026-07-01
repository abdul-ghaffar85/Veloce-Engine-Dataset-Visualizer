# ═══════════════════════════════════════════════════════════════════════════════
# Veloce Engine — Correlation & Trends Schemas
# ═══════════════════════════════════════════════════════════════════════════════
"""
Pydantic v2 schemas for the Correlation Engine.

These models define responses for correlation matrices, feature importance
rankings, and time-series trend analysis.
"""

from __future__ import annotations

import enum

from pydantic import BaseModel, Field


# ═══════════════════════════════════════════════════════════════════════════════
# Enums
# ═══════════════════════════════════════════════════════════════════════════════

class TrendDirection(str, enum.Enum):
    """Direction of a time-series trend."""
    UP = "up"
    DOWN = "down"
    FLAT = "flat"


class CorrelationDirection(str, enum.Enum):
    """Direction of feature importance / correlation."""
    POSITIVE = "positive"
    NEGATIVE = "negative"
    NEUTRAL = "neutral"


# ═══════════════════════════════════════════════════════════════════════════════
# Correlation Matrix
# ═══════════════════════════════════════════════════════════════════════════════

class CorrelationMatrixEntry(BaseModel):
    """A single cell in the correlation matrix."""
    column_x: str
    column_y: str
    pearson: float | None = Field(description="Linear correlation (-1.0 to 1.0).")
    spearman: float | None = Field(description="Rank correlation (-1.0 to 1.0).")


class CorrelationMatrixResponse(BaseModel):
    """API response wrapper for the correlation matrix."""
    status: str = "success"
    dataset_id: str
    matrix: list[CorrelationMatrixEntry] = Field(
        description="Flattened upper-triangle of the correlation matrix."
    )


# ═══════════════════════════════════════════════════════════════════════════════
# Feature Importance
# ═══════════════════════════════════════════════════════════════════════════════

class FeatureImportance(BaseModel):
    """Predictive importance of a feature relative to a target."""
    feature: str
    importance_score: float = Field(description="Normalized importance (0.0 to 1.0).")
    direction: CorrelationDirection
    method: str = Field(description="Statistical method used (e.g., 'pearson', 'anova_eta_squared').")


class FeatureImportanceResponse(BaseModel):
    """API response wrapper for feature importance."""
    status: str = "success"
    dataset_id: str
    target_column: str
    importances: list[FeatureImportance] = Field(
        description="Features ranked by importance descending."
    )


# ═══════════════════════════════════════════════════════════════════════════════
# Time-Series Trends
# ═══════════════════════════════════════════════════════════════════════════════

class TrendAnalysis(BaseModel):
    """Trend analysis for a specific measure over time."""
    time_column: str
    measure_column: str
    direction: TrendDirection
    slope: float = Field(description="Linear regression slope.")
    total_percentage_change: float = Field(description="Percentage change from start to end.")
    is_significant: bool = Field(description="True if the trend is statistically/practically significant.")


class TrendAnalysisResponse(BaseModel):
    """API response wrapper for dataset trends."""
    status: str = "success"
    dataset_id: str
    trends: list[TrendAnalysis]
