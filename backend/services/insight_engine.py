# ═══════════════════════════════════════════════════════════════════════════════
# Veloce Engine — AI Insight Engine Service
# ═══════════════════════════════════════════════════════════════════════════════
"""
Automatic Natural Language Insight Generation Engine.

Synthesizes data from the Profiler, Semantic, and Correlation engines to
generate human-readable observations about data quality, trends, correlations,
and distributions.

Usage::

    from backend.services.insight_engine import get_insight_engine

    engine = get_insight_engine()
    insights = await engine.generate_insights(dataset_id, df)
"""

from __future__ import annotations

import asyncio
from typing import Any

import pandas as pd

from backend.core.exceptions import DataProcessingError
from backend.core.logging import get_logger
from backend.schemas.correlation import TrendDirection
from backend.schemas.insights import (
    Insight,
    InsightSeverity,
    InsightsResponse,
    InsightType,
)
from backend.schemas.semantic import BusinessEntity
from backend.services.correlation_engine import get_correlation_engine
from backend.services.profiler import ProfilingService

from backend.services.semantic_engine import get_semantic_engine

_logger = get_logger(__name__)


# ═══════════════════════════════════════════════════════════════════════════════
# AI Insight Engine Service
# ═══════════════════════════════════════════════════════════════════════════════

class InsightEngineService:
    """
    Stateless Natural Language Generation (NLG) rule engine for dataset analytics.
    """

    async def generate_insights(self, dataset_id: str, df: pd.DataFrame, filename: str | None = None) -> InsightsResponse:
        """Generate all insights by orchestrating underlying statistical engines."""
        try:
            return await asyncio.to_thread(self._generate_sync, dataset_id, df, filename)
        except Exception as exc:
            _logger.exception("insight_generation_failed", dataset_id=dataset_id, error=str(exc))
            raise DataProcessingError("Failed to generate AI insights.", str(exc)) from exc

    # ─── Synchronous Implementation ────────────────────────────────

    def _generate_sync(self, dataset_id: str, df: pd.DataFrame, filename: str | None = None) -> InsightsResponse:
        _logger.info("generating_insights", dataset_id=dataset_id)

        # 1. Gather all analytical metadata
        profiler = ProfilingService()
        semantic = get_semantic_engine()
        correlator = get_correlation_engine()

        profile = profiler._profile_sync(dataset_id, filename or dataset_id, df)
        semantics = semantic._analyze_sync(dataset_id, df)
        corr_matrix = correlator._matrix_sync(dataset_id, df)
        trends = correlator._trends_sync(dataset_id, df, time_column=None)

        insights: list[Insight] = []

        # 2. Synthesize Insights
        insights.extend(self._generate_data_quality_insights(profile))
        insights.extend(self._generate_semantic_insights(semantics))
        insights.extend(self._generate_correlation_insights(corr_matrix))
        insights.extend(self._generate_trend_insights(trends))

        # Sort insights by severity: CRITICAL > WARNING > SUCCESS > INFO
        severity_rank = {
            InsightSeverity.CRITICAL: 1,
            InsightSeverity.WARNING: 2,
            InsightSeverity.SUCCESS: 3,
            InsightSeverity.INFO: 4,
        }
        insights.sort(key=lambda x: severity_rank[x.severity])

        return InsightsResponse(dataset_id=dataset_id, insights=insights)

    # ─── Generators ───────────────────────────────────────────────

    def _generate_data_quality_insights(self, profile: Any) -> list[Insight]:
        insights = []
        total_rows = profile.row_count
        if total_rows == 0:
            return insights

        for col in profile.columns:
            null_pct = (col.missing.count / total_rows) * 100 if total_rows > 0 else 0.0

            if null_pct > 50:
                insights.append(
                    Insight(
                        insight_type=InsightType.DATA_QUALITY,
                        severity=InsightSeverity.CRITICAL,
                        title=f"High Missing Data: {col.name}",
                        description=f"The '{col.name}' column is missing {null_pct:.1f}% of its values. Consider imputing or removing this column before analysis.",
                        related_columns=[col.name],
                    )
                )
            elif null_pct > 10:
                insights.append(
                    Insight(
                        insight_type=InsightType.DATA_QUALITY,
                        severity=InsightSeverity.WARNING,
                        title=f"Moderate Missing Data: {col.name}",
                        description=f"The '{col.name}' column is missing {null_pct:.1f}% of its values.",
                        related_columns=[col.name],
                    )
                )

            if col.is_constant:
                insights.append(
                    Insight(
                        insight_type=InsightType.DISTRIBUTION,
                        severity=InsightSeverity.INFO,
                        title=f"Constant Value: {col.name}",
                        description=f"The '{col.name}' column contains exactly the same value for every row, offering no variance.",
                        related_columns=[col.name],
                    )
                )

        return insights

    def _generate_semantic_insights(self, semantics: Any) -> list[Insight]:
        insights = []
        pii_entities = {
            BusinessEntity.EMAIL,
            BusinessEntity.PHONE_NUMBER,
            BusinessEntity.CREDIT_CARD,
            BusinessEntity.SSN,
        }

        pii_cols = []
        for col in semantics.columns:
            if col.entity_type in pii_entities and col.confidence > 0.6:
                pii_cols.append(col.column_name)

        if pii_cols:
            insights.append(
                Insight(
                    insight_type=InsightType.SEMANTIC,
                    severity=InsightSeverity.WARNING,
                    title="PII Data Detected",
                    description=f"Detected potentially sensitive Personally Identifiable Information (PII) in columns: {', '.join(pii_cols)}. Ensure this data complies with GDPR/CCPA regulations.",
                    related_columns=pii_cols,
                )
            )

        geo_cols = [c.column_name for c in semantics.columns if c.entity_type in {BusinessEntity.LATITUDE, BusinessEntity.LONGITUDE, BusinessEntity.CITY, BusinessEntity.COUNTRY}]
        if geo_cols:
             insights.append(
                Insight(
                    insight_type=InsightType.SEMANTIC,
                    severity=InsightSeverity.INFO,
                    title="Geospatial Data Available",
                    description=f"Detected location-based columns ({', '.join(geo_cols)}). This dataset is suitable for map-based visualizations.",
                    related_columns=geo_cols,
                )
            )

        return insights

    def _generate_correlation_insights(self, corr_matrix: Any) -> list[Insight]:
        insights = []
        
        if not corr_matrix.matrix:
            return insights

        for corr in corr_matrix.matrix:
            if corr.pearson is None:
                continue

            # Strong Positive
            if corr.pearson > 0.85:
                insights.append(
                    Insight(
                        insight_type=InsightType.CORRELATION,
                        severity=InsightSeverity.SUCCESS,
                        title="Strong Positive Correlation",
                        description=f"'{corr.column_x}' and '{corr.column_y}' move together very closely (Pearson: {corr.pearson:.2f}). Increases in one usually indicate increases in the other.",
                        related_columns=[corr.column_x, corr.column_y],
                    )
                )
            # Strong Negative
            elif corr.pearson < -0.85:
                insights.append(
                    Insight(
                        insight_type=InsightType.CORRELATION,
                        severity=InsightSeverity.INFO,
                        title="Strong Inverse Correlation",
                        description=f"'{corr.column_x}' and '{corr.column_y}' have a strong inverse relationship (Pearson: {corr.pearson:.2f}). As one increases, the other typically decreases.",
                        related_columns=[corr.column_x, corr.column_y],
                    )
                )
        return insights

    def _generate_trend_insights(self, trends: Any) -> list[Insight]:
        insights = []

        if not trends.trends:
            return insights

        for trend in trends.trends:
            if trend.is_significant:
                if trend.direction == TrendDirection.UP:
                    insights.append(
                        Insight(
                            insight_type=InsightType.TREND,
                            severity=InsightSeverity.SUCCESS,
                            title=f"{trend.measure_column.title()} is Trending UP",
                            description=f"'{trend.measure_column}' shows a significant upward trend of +{trend.total_percentage_change:.1f}% over time based on '{trend.time_column}'.",
                            related_columns=[trend.measure_column, trend.time_column],
                        )
                    )
                elif trend.direction == TrendDirection.DOWN:
                    insights.append(
                        Insight(
                            insight_type=InsightType.TREND,
                            severity=InsightSeverity.WARNING,
                            title=f"{trend.measure_column.title()} is Trending DOWN",
                            description=f"'{trend.measure_column}' shows a significant downward trend of {trend.total_percentage_change:.1f}% over time based on '{trend.time_column}'.",
                            related_columns=[trend.measure_column, trend.time_column],
                        )
                    )

        return insights


# ─── Module-level Singleton ──────────────────────────────────────────────────

_insight_engine: InsightEngineService | None = None

def get_insight_engine() -> InsightEngineService:
    global _insight_engine
    if _insight_engine is None:
        _insight_engine = InsightEngineService()
    return _insight_engine
