# ═══════════════════════════════════════════════════════════════════════════════
# Veloce Engine — Aggregation Engine Service
# ═══════════════════════════════════════════════════════════════════════════════
"""
Automatic Data Aggregation and Querying Engine.

Translates declarative JSON query payloads into optimized Pandas operations.
Handles row filtering, dimension grouping, measure aggregation, sorting,
and pagination. Computations run asynchronously in a thread pool.

Usage::

    from backend.services.aggregation_engine import get_aggregation_engine

    engine = get_aggregation_engine()
    response = await engine.execute_query(dataset_id, df, query_request)
"""

from __future__ import annotations

import asyncio
import time
from typing import Any

import numpy as np
import pandas as pd

from backend.core.exceptions import DataProcessingError
from backend.core.logging import get_logger
from backend.schemas.aggregation import (
    FilterOperator,
    QueryRequest,
    QueryResponse,
    SortOrder,
)

_logger = get_logger(__name__)


# ═══════════════════════════════════════════════════════════════════════════════
# Aggregation Engine Service
# ═══════════════════════════════════════════════════════════════════════════════

class AggregationEngineService:
    """
    Stateless query execution engine for DataFrames.
    Executes all Pandas operations in a thread pool to avoid blocking the event loop.
    """

    async def execute_query(
        self,
        dataset_id: str,
        df: pd.DataFrame,
        query: QueryRequest,
    ) -> QueryResponse:
        """
        Execute a dynamic query payload on a Pandas DataFrame asynchronously.
        """
        try:
            return await asyncio.to_thread(self._execute_sync, dataset_id, df, query)
        except Exception as exc:
            _logger.exception("query_execution_failed", dataset_id=dataset_id, error=str(exc))
            raise DataProcessingError(
                message="Failed to execute aggregation query.",
                internal=str(exc),
            ) from exc

    # ─── Synchronous Execution Pipeline ──────────────────────────────

    def _execute_sync(
        self,
        dataset_id: str,
        df: pd.DataFrame,
        query: QueryRequest,
    ) -> QueryResponse:
        
        start = time.perf_counter()
        
        _logger.info(
            "executing_query",
            dataset_id=dataset_id,
            filters=len(query.filters),
            group_by=len(query.group_by),
            aggregates=len(query.aggregates),
        )

        # 1. Row-level Filtering
        filtered_df = self._apply_filters(df, query)
        total_matched_rows = len(filtered_df)

        # 2. Grouping & Aggregation
        agg_df = self._apply_aggregations(filtered_df, query)

        # 3. Sorting
        sorted_df = self._apply_sort(agg_df, query)

        # 4. Pagination
        paginated_df = sorted_df.iloc[query.offset : query.offset + query.limit]

        # 5. Serialization prep (Handle NaNs/Infs for JSON compatibility)
        paginated_df = paginated_df.replace([np.inf, -np.inf], np.nan)
        # Using `where` with `pd.notnull` handles both np.nan and pd.NaT gracefully
        paginated_df = paginated_df.where(pd.notnull(paginated_df), None)

        data = paginated_df.to_dict(orient="records")

        duration_ms = (time.perf_counter() - start) * 1000

        _logger.info("final_visualization_json", dataset_id=dataset_id, total_rows=total_matched_rows, returned_rows=len(data), preview=data[:5])

        return QueryResponse(
            dataset_id=dataset_id,
            total_rows=total_matched_rows,
            returned_rows=len(data),
            data=data,
            execution_time_ms=round(duration_ms, 2),
        )

    # ─── Internal Implementation Details ─────────────────────────────

    def _apply_filters(self, df: pd.DataFrame, query: QueryRequest) -> pd.DataFrame:
        """Apply row-level WHERE conditions."""
        if not query.filters or df.empty:
            return df

        mask = pd.Series(True, index=df.index)

        for f in query.filters:
            col = f.column
            if col not in df.columns:
                continue

            op = f.operator
            val = f.value

            try:
                if op == FilterOperator.EQ:
                    mask &= (df[col] == val)
                elif op == FilterOperator.NEQ:
                    mask &= (df[col] != val)
                elif op == FilterOperator.GT:
                    mask &= (df[col] > val)
                elif op == FilterOperator.GTE:
                    mask &= (df[col] >= val)
                elif op == FilterOperator.LT:
                    mask &= (df[col] < val)
                elif op == FilterOperator.LTE:
                    mask &= (df[col] <= val)
                elif op == FilterOperator.IN:
                    if isinstance(val, list):
                        mask &= df[col].isin(val)
                elif op == FilterOperator.NOT_IN:
                    if isinstance(val, list):
                        mask &= ~df[col].isin(val)
                elif op == FilterOperator.CONTAINS:
                    mask &= df[col].astype(str).str.contains(str(val), case=False, na=False)
                elif op == FilterOperator.IS_NULL:
                    mask &= df[col].isna()
                elif op == FilterOperator.NOT_NULL:
                    mask &= df[col].notna()
            except Exception:
                # If a specific filter fails (e.g. type mismatch), log it and continue
                # In production, we might want to raise a ValidationError instead
                _logger.warning("filter_application_failed", column=col, operator=op.value, value=val)

        return df[mask]

    def _apply_aggregations(self, df: pd.DataFrame, query: QueryRequest) -> pd.DataFrame:
        """Apply GROUP BY and SELECT metric aggregations."""
        if df.empty:
            return df
            
        group_cols = [c for c in query.group_by if c in df.columns]

        # 1. Column Type Detection & Numeric Conversion for Metrics
        # Pre-process aggregate columns to ensure they are numeric before applying sum/mean etc.
        agg_cols = {agg.column for agg in query.aggregates if agg.column in df.columns}
        for col in agg_cols:
            _logger.debug("detected_metric_dtype", column=col, original_dtype=str(df[col].dtype))
            # Coerce to numeric, turning invalid parsing into NaN
            df[col] = pd.to_numeric(df[col], errors='coerce')

        # 2. Null Handling & Category Normalization for Dimensions
        for col in group_cols:
            if df[col].dtype == 'object' or pd.api.types.is_string_dtype(df[col]):
                # Fill nulls with 'Unknown'
                df[col] = df[col].fillna('Unknown')
                # Normalize categories (strip whitespace, capitalize)
                df[col] = df[col].astype(str).str.strip().str.title()
            else:
                # For non-string columns, fillna with a placeholder or dropna=False handles it
                df[col] = df[col].fillna('Unknown')

        # Prepare NamedAgg kwargs
        agg_kwargs = {}
        for agg in query.aggregates:
            if agg.column not in df.columns:
                continue
                
            # IMPORTANT: The frontend uses the exact yAxis field name (e.g. "Sale Price") to extract the value.
            # If we alias it to "Sale Price_sum", the frontend gets undefined and renders 0.
            # We use the original column name as the alias if only one aggregation is applied per column,
            # or the explicitly provided alias.
            alias = agg.alias or agg.column
            
            # Prevent duplicate alias collision if multiple aggregations are performed on the same column
            if alias in agg_kwargs:
                alias = f"{agg.column}_{agg.function.value}"
                
            agg_kwargs[alias] = pd.NamedAgg(column=agg.column, aggfunc=agg.function.value)

        # Apply Aggregations
        if group_cols and agg_kwargs:
            _logger.info("aggregation_method", type="group_by_and_agg", group_cols=group_cols, aggregates=list(agg_kwargs.keys()))
            result_df = df.groupby(group_cols, as_index=False, dropna=False).agg(**agg_kwargs)
        elif group_cols and not agg_kwargs:
            _logger.info("aggregation_method", type="group_by_only", group_cols=group_cols)
            result_df = df[group_cols].drop_duplicates().reset_index(drop=True)
        elif not group_cols and agg_kwargs:
            _logger.info("aggregation_method", type="global_agg", aggregates=list(agg_kwargs.keys()))
            res_row = {}
            for alias, named_agg in agg_kwargs.items():
                res_row[alias] = df[named_agg.column].agg(named_agg.aggfunc)
            result_df = pd.DataFrame([res_row])
        else:
            _logger.info("aggregation_method", type="none")
            result_df = df

        # Log grouped dataframe
        _logger.info("grouped_dataframe", head=result_df.head().to_dict(orient="records"))
        
        return result_df

    def _apply_sort(self, df: pd.DataFrame, query: QueryRequest) -> pd.DataFrame:
        """Apply ORDER BY conditions."""
        if not query.sort or df.empty:
            return df

        sort_cols = []
        sort_asc = []

        for s in query.sort:
            if s.column in df.columns:
                sort_cols.append(s.column)
                sort_asc.append(s.order == SortOrder.ASC)

        if sort_cols:
            return df.sort_values(by=sort_cols, ascending=sort_asc)

        return df


# ─── Module-level Singleton ──────────────────────────────────────────────────

_aggregation_engine: AggregationEngineService | None = None

def get_aggregation_engine() -> AggregationEngineService:
    global _aggregation_engine
    if _aggregation_engine is None:
        _aggregation_engine = AggregationEngineService()
    return _aggregation_engine
