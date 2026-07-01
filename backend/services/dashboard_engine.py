# ═══════════════════════════════════════════════════════════════════════════════
# Veloce Engine — Dashboard Generator Service
# ═══════════════════════════════════════════════════════════════════════════════
"""
Automatic Dashboard Generator.

This engine orchestrates the Profiler, Semantic, and Correlation engines to
synthesize a declarative dashboard layout (JSON). It uses heuristics to pick
the best dimensions for filters, the most important measures for KPI cards,
and the most insightful relationships for charts.

Usage::

    from backend.services.dashboard_engine import get_dashboard_engine

    engine = get_dashboard_engine()
    layout = await engine.generate_dashboard(dataset_id, df)
"""

from __future__ import annotations

import asyncio
import uuid
from typing import Any

import pandas as pd

from backend.core.exceptions import DataProcessingError
from backend.core.logging import get_logger
from backend.schemas.dashboard import (
    ChartConfig,
    ChartType,
    DashboardFilter,
    DashboardLayout,
    FilterType,
    KpiCard,
)
from backend.schemas.profile import ColumnRole
from backend.services.profiler import ProfilingService
from backend.services.correlation_engine import get_correlation_engine

_logger = get_logger(__name__)


# ═══════════════════════════════════════════════════════════════════════════════
# Dashboard Generator Service
# ═══════════════════════════════════════════════════════════════════════════════

class DashboardGeneratorService:
    """
    Stateless engine to intelligently generate dashboard configurations.
    """

    async def generate_dashboard(
        self,
        dataset_id: str,
        df: pd.DataFrame,
        filename: str | None = None,
    ) -> DashboardLayout:
        """
        Orchestrate metadata extraction and synthesize a dashboard configuration.
        """
        try:
            return await asyncio.to_thread(self._generate_sync, dataset_id, df, filename)
        except Exception as exc:
            _logger.exception("dashboard_generation_failed", dataset_id=dataset_id, error=str(exc))
            raise DataProcessingError("Failed to generate dashboard layout.", str(exc)) from exc

    # ─── Synchronous Implementation ────────────────────────────────

    def _generate_sync(self, dataset_id: str, df: pd.DataFrame, filename: str | None = None) -> DashboardLayout:
        _logger.info("generating_dashboard", dataset_id=dataset_id)

        # 1. Fetch metadata from the profiler.
        profiler = ProfilingService()
        correlator = get_correlation_engine()

        profile = profiler._profile_sync(dataset_id, filename or dataset_id, df)

        dimensions: list[Any] = []
        measures: list[Any] = []
        time_cols: list[Any] = []

        for col in profile.columns:
            if col.role == ColumnRole.TIME:
                time_cols.append(col)
            elif col.role == ColumnRole.MEASURE:
                measures.append(col)
            else:
                dimensions.append(col)

        # Heuristic 1: Choose the primary time column (if any)
        primary_time_col = time_cols[0].name if time_cols else None

        # 2. Build Components
        filters = self._build_filters(dimensions, time_cols)
        kpi_cards = self._build_kpis(measures, primary_time_col)
        charts = self._build_charts(dimensions, measures, time_cols, correlator, dataset_id, df)

        title = f"Data Insights: {profile.filename}"

        return DashboardLayout(
            dataset_id=dataset_id,
            title=title,
            filters=filters,
            kpi_cards=kpi_cards,
            charts=charts,
        )

    # ─── Heuristic Builders ────────────────────────────────────────

    def _build_filters(self, dimensions: list[Any], time_cols: list[Any]) -> list[DashboardFilter]:
        filters = []

        # Time Filters
        for tc in time_cols[:1]:  # Max 1 global date filter
            filters.append(
                DashboardFilter(
                    column=tc.name,
                    filter_type=FilterType.DATE_RANGE,
                    label=f"{tc.name.replace('_', ' ').title()} Range"
                )
            )

        # Categorical Filters (choose dimensions with low cardinality but not single-value)
        candidate_dims = [d for d in dimensions if 1 < d.unique_count <= 20 and not d.is_constant]
        # Sort by uniqueness (fewer options = better for top-level dropdowns)
        candidate_dims.sort(key=lambda x: x.unique_count)

        for dim in candidate_dims[:3]:  # Max 3 dropdowns to avoid clutter
            filters.append(
                DashboardFilter(
                    column=dim.name,
                    filter_type=FilterType.MULTI_SELECT,
                    label=dim.name.replace('_', ' ').title()
                )
            )

        return filters

    def _build_kpis(self, measures: list[Any], primary_time_col: str | None) -> list[KpiCard]:
        kpis = []

        # Sort measures by fewest nulls, then assume those are most critical.
        valid_measures = [m for m in measures if m.missing.count < m.total_count]
        valid_measures.sort(key=lambda x: (x.missing.count, -x.unique_count))

        for m in valid_measures[:4]:  # Max 4 KPIs
            kpis.append(
                KpiCard(
                    id=f"kpi_{uuid.uuid4().hex[:8]}",
                    title=f"Total {m.name.replace('_', ' ').title()}",
                    measure_column=m.name,
                    aggregation="sum",
                    format_as="currency" if "amount" in m.name.lower() or "price" in m.name.lower() else "number",
                    trend_column=primary_time_col
                )
            )

        return kpis

    def _build_charts(
        self,
        dimensions: list[Any],
        measures: list[Any],
        time_cols: list[Any],
        correlator: Any,
        dataset_id: str,
        df: pd.DataFrame
    ) -> list[ChartConfig]:
        charts = []

        if not measures:
            return charts

        primary_measure = measures[0].name

        # 1. Time-Series Line Chart
        if time_cols:
            tc = time_cols[0].name
            charts.append(
                ChartConfig(
                    id=f"chart_{uuid.uuid4().hex[:8]}",
                    title=f"{primary_measure.replace('_', ' ').title()} Over Time",
                    chart_type=ChartType.LINE,
                    x_axis=tc,
                    y_axis=[primary_measure],
                    aggregation="sum",
                    description="Visualizes the historical trend of the primary metric."
                )
            )
            
        # 2. Categorical Bar Charts
        categorical_dims = [d for d in dimensions if 2 <= d.unique_count <= 15 and not d.is_constant]
        if categorical_dims:
            # Take the dimension with the most variance
            dim = categorical_dims[0].name
            charts.append(
                ChartConfig(
                    id=f"chart_{uuid.uuid4().hex[:8]}",
                    title=f"{primary_measure.replace('_', ' ').title()} by {dim.replace('_', ' ').title()}",
                    chart_type=ChartType.BAR,
                    x_axis=dim,
                    y_axis=[primary_measure],
                    aggregation="sum",
                    description=f"Breaks down total {primary_measure} across {dim} categories."
                )
            )

            # If we have a very low cardinality dim (< 6), make a Donut chart
            micro_dims = [d for d in categorical_dims if d.unique_count <= 5]
            if micro_dims and len(measures) > 1:
                sec_measure = measures[1].name
                md = micro_dims[0].name
                charts.append(
                    ChartConfig(
                        id=f"chart_{uuid.uuid4().hex[:8]}",
                        title=f"{sec_measure.replace('_', ' ').title()} Distribution by {md.replace('_', ' ').title()}",
                        chart_type=ChartType.DONUT,
                        x_axis=md,
                        y_axis=[sec_measure],
                        aggregation="sum"
                    )
                )

        # 3. Correlation Scatter Plot
        if len(measures) >= 2:
            # Use the correlation engine to find the strongest correlation
            corr_resp = correlator._matrix_sync(dataset_id, df)
            if corr_resp.matrix:
                # Find strongest absolute pearson correlation < 1.0 (avoid self-correlation if passed)
                valid_corrs = [c for c in corr_resp.matrix if c.pearson is not None and abs(c.pearson) < 0.99]
                if valid_corrs:
                    valid_corrs.sort(key=lambda x: abs(x.pearson), reverse=True)
                    best_corr = valid_corrs[0]
                    
                    charts.append(
                    ChartConfig(
                        id=f"chart_{uuid.uuid4().hex[:8]}",
                        title=f"Correlation: {best_corr.column_x} vs {best_corr.column_y}",
                        chart_type=ChartType.SCATTER,
                        x_axis=best_corr.column_x,
                        y_axis=[best_corr.column_y],
                        aggregation="none",  # Scatter plots use raw points.
                        description=f"Shows the linear relationship (Pearson: {round(best_corr.pearson, 2)})."
                    )
                )

        # 4. Detail Data Grid
        charts.append(
            ChartConfig(
                id=f"chart_{uuid.uuid4().hex[:8]}",
                title="Detailed Records",
                chart_type=ChartType.TABLE,
                description="Raw data grid supporting sorting, filtering, and pagination."
            )
        )

        return charts


# ─── Module-level Singleton ──────────────────────────────────────────────────

_dashboard_engine: DashboardGeneratorService | None = None

def get_dashboard_engine() -> DashboardGeneratorService:
    global _dashboard_engine
    if _dashboard_engine is None:
        _dashboard_engine = DashboardGeneratorService()
    return _dashboard_engine
