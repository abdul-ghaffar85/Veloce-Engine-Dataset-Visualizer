# ═══════════════════════════════════════════════════════════════════════════════
# Veloce Engine — Correlation Engine Service
# ═══════════════════════════════════════════════════════════════════════════════
"""
Automatic Correlation and Trend Analysis Engine.

Performs statistical analysis on datasets to extract insights:
1. Correlation Matrix (Pearson & Spearman for all numeric columns).
2. Feature Importance (Predictive power of columns relative to a target).
3. Time-Series Trends (Linear regression slope and percentage change).

Computations run asynchronously in a thread pool using optimized NumPy operations.

Usage::

    from backend.services.correlation_engine import get_correlation_engine

    engine = get_correlation_engine()
    matrix = await engine.get_correlation_matrix(dataset_id, df)
    importance = await engine.get_feature_importance(dataset_id, df, target="Sales")
    trends = await engine.analyze_trends(dataset_id, df, time_col="Date")
"""

from __future__ import annotations

import asyncio
import math
import time
from typing import Any

import numpy as np
import pandas as pd

from backend.core.exceptions import DataProcessingError
from backend.core.logging import get_logger
from backend.schemas.correlation import (
    CorrelationDirection,
    CorrelationMatrixEntry,
    CorrelationMatrixResponse,
    FeatureImportance,
    FeatureImportanceResponse,
    TrendAnalysis,
    TrendAnalysisResponse,
    TrendDirection,
)

_logger = get_logger(__name__)


# ═══════════════════════════════════════════════════════════════════════════════
# Correlation Engine Service
# ═══════════════════════════════════════════════════════════════════════════════

class CorrelationEngineService:
    """
    Stateless engine for correlation, feature importance, and trend analysis.
    """

    async def get_correlation_matrix(
        self,
        dataset_id: str,
        df: pd.DataFrame,
    ) -> CorrelationMatrixResponse:
        try:
            return await asyncio.to_thread(self._matrix_sync, dataset_id, df)
        except Exception as exc:
            _logger.exception("correlation_matrix_failed", error=str(exc))
            raise DataProcessingError("Failed to calculate correlation matrix.", str(exc)) from exc

    async def get_feature_importance(
        self,
        dataset_id: str,
        df: pd.DataFrame,
        target_column: str,
    ) -> FeatureImportanceResponse:
        try:
            return await asyncio.to_thread(self._importance_sync, dataset_id, df, target_column)
        except Exception as exc:
            _logger.exception("feature_importance_failed", error=str(exc))
            raise DataProcessingError("Failed to calculate feature importance.", str(exc)) from exc

    async def analyze_trends(
        self,
        dataset_id: str,
        df: pd.DataFrame,
        time_column: str | None = None,
    ) -> TrendAnalysisResponse:
        try:
            return await asyncio.to_thread(self._trends_sync, dataset_id, df, time_column)
        except Exception as exc:
            _logger.exception("trend_analysis_failed", error=str(exc))
            raise DataProcessingError("Failed to analyze trends.", str(exc)) from exc

    # ─── Synchronous Implementations ──────────────────────────────

    def _matrix_sync(self, dataset_id: str, df: pd.DataFrame) -> CorrelationMatrixResponse:
        numeric_df = df.select_dtypes(include=[np.number])
        if numeric_df.empty or len(numeric_df.columns) < 2:
            return CorrelationMatrixResponse(dataset_id=dataset_id, matrix=[])

        pearson_mat = numeric_df.corr(method="pearson")
        spearman_mat = numeric_df.corr(method="spearman")

        matrix = []
        cols = pearson_mat.columns
        for i in range(len(cols)):
            for j in range(i + 1, len(cols)):
                col_a = cols[i]
                col_b = cols[j]
                
                p_val = pearson_mat.iloc[i, j]
                s_val = spearman_mat.iloc[i, j]

                matrix.append(
                    CorrelationMatrixEntry(
                        column_x=col_a,
                        column_y=col_b,
                        pearson=float(p_val) if pd.notna(p_val) else None,
                        spearman=float(s_val) if pd.notna(s_val) else None,
                    )
                )

        return CorrelationMatrixResponse(dataset_id=dataset_id, matrix=matrix)

    def _importance_sync(
        self, dataset_id: str, df: pd.DataFrame, target_column: str
    ) -> FeatureImportanceResponse:
        if target_column not in df.columns:
            raise ValueError(f"Target column '{target_column}' not found.")

        target_series = df[target_column]
        is_target_numeric = pd.api.types.is_numeric_dtype(target_series)
        
        importances = []

        for col in df.columns:
            if col == target_column:
                continue

            feature_series = df[col]
            is_feature_numeric = pd.api.types.is_numeric_dtype(feature_series)

            score = 0.0
            direction = CorrelationDirection.NEUTRAL
            method = "unknown"

            # 1. Numeric Target vs Numeric Feature -> Absolute Pearson
            if is_target_numeric and is_feature_numeric:
                corr = target_series.corr(feature_series, method="pearson")
                if pd.notna(corr):
                    score = abs(corr)
                    direction = CorrelationDirection.POSITIVE if corr > 0 else CorrelationDirection.NEGATIVE
                    method = "pearson"

            # 2. Numeric Target vs Categorical Feature -> ANOVA Eta-Squared
            elif is_target_numeric and not is_feature_numeric:
                score = self._anova_eta_squared(feature_series, target_series)
                method = "anova_eta_squared"
                direction = CorrelationDirection.POSITIVE # ANOVA doesn't have direction

            # 3. Categorical Target vs Numeric Feature -> ANOVA Eta-Squared (Reversed)
            elif not is_target_numeric and is_feature_numeric:
                score = self._anova_eta_squared(target_series, feature_series)
                method = "anova_eta_squared"
                direction = CorrelationDirection.POSITIVE

            # We skip Categorical vs Categorical for now to keep heuristics fast and robust

            if score > 0.0:
                importances.append(
                    FeatureImportance(
                        feature=col,
                        importance_score=round(score, 4),
                        direction=direction,
                        method=method,
                    )
                )

        # Sort descending by importance
        importances.sort(key=lambda x: x.importance_score, reverse=True)

        return FeatureImportanceResponse(
            dataset_id=dataset_id,
            target_column=target_column,
            importances=importances,
        )

    def _trends_sync(
        self, dataset_id: str, df: pd.DataFrame, time_column: str | None
    ) -> TrendAnalysisResponse:
        
        # If no time column specified, try to find one automatically
        if not time_column:
            datetime_cols = df.select_dtypes(include=["datetime", "datetimetz"]).columns
            if len(datetime_cols) > 0:
                time_column = datetime_cols[0]
            else:
                # Try to parse string columns that look like dates
                for col in df.columns:
                    if pd.api.types.is_string_dtype(df[col]):
                        try:
                            # Quick check on first non-null
                            first_val = df[col].dropna().iloc[0]
                            pd.to_datetime(first_val)
                            time_column = col
                            break
                        except Exception:
                            continue

        if not time_column or time_column not in df.columns:
            # Cannot perform trend analysis without a time column
            return TrendAnalysisResponse(dataset_id=dataset_id, trends=[])

        # Ensure the time series is represented as datetime without mutating
        # the stored DataFrame.
        if pd.api.types.is_datetime64_any_dtype(df[time_column]):
            time_series = df[time_column]
        else:
            time_series = pd.to_datetime(df[time_column], errors="coerce")

        trends = []
        numeric_cols = df.select_dtypes(include=[np.number]).columns

        for col in numeric_cols:
            if col == time_column:
                continue

            trend = self._calculate_single_trend(time_series, df[col], time_column, col)
            if trend:
                trends.append(trend)

        return TrendAnalysisResponse(dataset_id=dataset_id, trends=trends)

    # ─── Internal Statistical Methods ────────────────────────────

    def _anova_eta_squared(self, cat_series: pd.Series, num_series: pd.Series) -> float:
        """
        Calculates the ratio of variance explained by the categorical groups
        (Sum of Squares Between / Sum of Squares Total).
        Returns a value between 0.0 and 1.0.
        """
        df_clean = pd.DataFrame({"cat": cat_series, "num": num_series}).dropna()
        if df_clean.empty or df_clean["cat"].nunique() < 2:
            return 0.0
        
        mu = df_clean["num"].mean()
        sst = ((df_clean["num"] - mu) ** 2).sum()
        if sst == 0:
            return 0.0
            
        group_means = df_clean.groupby("cat")["num"].mean()
        group_counts = df_clean.groupby("cat")["num"].count()
        
        ssb = (group_counts * ((group_means - mu) ** 2)).sum()
        eta_sq = ssb / sst
        
        # Clamp to [0, 1] for safety against floating point anomalies
        return max(0.0, min(1.0, float(eta_sq)))

    def _calculate_single_trend(
        self, time_series: pd.Series, measure_series: pd.Series, time_col_name: str, measure_col_name: str
    ) -> TrendAnalysis | None:
        """
        Calculates the linear trend slope and percentage change over time.
        """
        df_clean = pd.DataFrame({"t": time_series, "y": measure_series}).dropna()
        df_clean = df_clean.sort_values("t")
        
        if len(df_clean) < 3:
            return None
            
        # Group by time to handle multiple observations per timestamp (use mean)
        grouped = df_clean.groupby("t")["y"].mean().reset_index()
        
        if len(grouped) < 3:
            return None

        t_min = grouped["t"].min()
        
        # X is days since the earliest timestamp
        x = (grouped["t"] - t_min).dt.days.values
        y = grouped["y"].values
        
        if len(np.unique(x)) < 2:
            return None
            
        # Fit linear regression line y = mx + c
        slope, intercept = np.polyfit(x, y, 1)
        
        # Calculate overall percentage change using the fitted line to avoid noise
        y_start_fit = intercept
        y_end_fit = (slope * x[-1]) + intercept
        
        pct_change = ((y_end_fit - y_start_fit) / abs(y_start_fit) * 100) if abs(y_start_fit) > 0.001 else 0.0
        
        direction = TrendDirection.FLAT
        if slope > 0 and pct_change > 2.0:
            direction = TrendDirection.UP
        elif slope < 0 and pct_change < -2.0:
            direction = TrendDirection.DOWN
            
        # Check if the linear fit is actually descriptive (R-squared > 0.1)
        correlation_matrix = np.corrcoef(x, y)
        r_squared = correlation_matrix[0, 1] ** 2 if len(correlation_matrix) > 1 else 0.0
        
        is_significant = bool(r_squared > 0.1 and abs(pct_change) > 2.0)

        return TrendAnalysis(
            time_column=time_col_name,
            measure_column=measure_col_name,
            direction=direction,
            slope=float(slope),
            total_percentage_change=round(float(pct_change), 2),
            is_significant=is_significant,
        )


# ─── Module-level Singleton ──────────────────────────────────────────────────

_correlation_engine: CorrelationEngineService | None = None

def get_correlation_engine() -> CorrelationEngineService:
    global _correlation_engine
    if _correlation_engine is None:
        _correlation_engine = CorrelationEngineService()
    return _correlation_engine
