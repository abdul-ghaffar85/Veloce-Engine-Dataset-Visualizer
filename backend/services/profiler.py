# ═══════════════════════════════════════════════════════════════════════════════
# Veloce Engine — Profiling Engine
# ═══════════════════════════════════════════════════════════════════════════════
"""
Automatic dataset profiling service.

Analyses every column of a dataset and produces a comprehensive profile
including:

* Semantic type inference (numeric, categorical, datetime, boolean, text, ID)
* Missing value analysis with completeness scores
* Descriptive statistics (numeric and categorical)
* Cardinality analysis and uniqueness detection
* IQR-based outlier detection
* Automatic dimension / measure / time role classification

The profiler is stateless — it accepts a ``pd.DataFrame`` and returns a
``DatasetProfile``.  All Pandas/NumPy work is executed via
``asyncio.to_thread()`` so it never blocks the event loop.

Usage::

    from backend.services.profiler import ProfilingService

    service = ProfilingService()
    profile = await service.profile_dataset(dataset_id="abc", filename="sales.csv", df=df)
"""

from __future__ import annotations

import asyncio
import math
import time
import warnings
from datetime import datetime, timezone
from typing import Any

import numpy as np
import pandas as pd

from backend.core.exceptions import ProfilingError
from backend.core.logging import get_logger
from backend.schemas.profile import (
    CategoricalStats,
    ColumnProfile,
    ColumnRole,
    DatasetProfile,
    MissingValueInfo,
    NumericStats,
    OutlierInfo,
    SemanticType,
)

_logger = get_logger(__name__)

# ─── Heuristic Thresholds ────────────────────────────────────────────────────

# If a string column's cardinality ratio (unique / total) exceeds this
# threshold, it is classified as TEXT rather than CATEGORICAL.
_TEXT_CARDINALITY_THRESHOLD = 0.5

# If a string column's cardinality ratio exceeds this, it may be an IDENTIFIER.
_IDENTIFIER_CARDINALITY_THRESHOLD = 0.95

# Minimum number of rows to meaningfully classify cardinality-based types.
_MIN_ROWS_FOR_CARDINALITY = 5

# Maximum categorical unique values to consider for top-values reporting.
_MAX_TOP_VALUES = 15

# Common datetime column name patterns (case-insensitive).
_DATETIME_NAME_PATTERNS: tuple[str, ...] = (
    "date", "time", "datetime", "timestamp", "created", "updated",
    "modified", "at", "on", "_dt", "_ts", "year", "month", "day",
    "period", "quarter", "week",
)

# Common ID column name patterns (case-insensitive).
_ID_NAME_PATTERNS: tuple[str, ...] = (
    "id", "_id", "key", "code", "number", "num", "no", "index",
    "pk", "fk", "uuid", "guid", "sku", "barcode",
)


# ═══════════════════════════════════════════════════════════════════════════════
# Profiling Service
# ═══════════════════════════════════════════════════════════════════════════════

class ProfilingService:
    """
    Stateless dataset profiling service.

    Each method handles one aspect of profiling.  The public
    ``profile_dataset`` method orchestrates them all and returns a
    ``DatasetProfile``.
    """

    # ─── Public API ──────────────────────────────────────────────────

    async def profile_dataset(
        self,
        *,
        dataset_id: str,
        filename: str,
        df: pd.DataFrame,
    ) -> DatasetProfile:
        """
        Run the full profiling pipeline on a DataFrame.

        Executes all CPU-bound Pandas/NumPy work in a background thread.

        Args:
            dataset_id: Unique dataset identifier.
            filename:   Display name for the dataset.
            df:         The pandas DataFrame to profile.

        Returns:
            A complete ``DatasetProfile`` with per-column analysis.

        Raises:
            ProfilingError: If profiling fails.
        """
        try:
            profile = await asyncio.to_thread(
                self._profile_sync, dataset_id, filename, df,
            )
            return profile
        except ProfilingError:
            raise
        except Exception as exc:
            _logger.exception(
                "profiling_failed",
                dataset_id=dataset_id,
                error=str(exc),
            )
            raise ProfilingError(
                message="An error occurred while profiling the dataset.",
                internal=str(exc),
            ) from exc

    # ─── Synchronous Profiling Core ──────────────────────────────────

    def _profile_sync(
        self,
        dataset_id: str,
        filename: str,
        df: pd.DataFrame,
    ) -> DatasetProfile:
        """
        Synchronous profiling entry point — runs in a thread pool.

        This method is intentionally synchronous so it can be dispatched
        via ``asyncio.to_thread()`` without holding the GIL across awaits.
        """
        start = time.perf_counter()

        row_count = len(df)
        col_count = len(df.columns)

        _logger.info(
            "profiling_started",
            dataset_id=dataset_id,
            rows=row_count,
            columns=col_count,
        )

        # Profile each column.
        column_profiles: list[ColumnProfile] = []
        for idx, col_name in enumerate(df.columns):
            profile = self._profile_column(df[col_name], col_name, idx, row_count)
            column_profiles.append(profile)

        # Aggregate dataset-level metrics.
        total_missing = sum(cp.missing.count for cp in column_profiles)
        total_cells = row_count * col_count
        overall_completeness = (
            ((total_cells - total_missing) / total_cells * 100)
            if total_cells > 0
            else 100.0
        )

        # Memory usage.
        mem_bytes = int(df.memory_usage(deep=True).sum())

        # Role summaries.
        dimensions = [cp.name for cp in column_profiles if cp.role == ColumnRole.DIMENSION]
        measures = [cp.name for cp in column_profiles if cp.role == ColumnRole.MEASURE]
        time_cols = [cp.name for cp in column_profiles if cp.role == ColumnRole.TIME]
        identifiers = [cp.name for cp in column_profiles if cp.role == ColumnRole.IDENTIFIER]

        duration_ms = (time.perf_counter() - start) * 1000

        _logger.info(
            "profiling_completed",
            dataset_id=dataset_id,
            duration_ms=round(duration_ms, 2),
            dimensions=len(dimensions),
            measures=len(measures),
            time_columns=len(time_cols),
            identifiers=len(identifiers),
            overall_completeness=round(overall_completeness, 2),
        )

        return DatasetProfile(
            dataset_id=dataset_id,
            filename=filename,
            row_count=row_count,
            column_count=col_count,
            dimensions=dimensions,
            measures=measures,
            time_columns=time_cols,
            identifiers=identifiers,
            total_missing_cells=total_missing,
            total_cells=total_cells,
            overall_completeness=round(overall_completeness, 2),
            memory_usage_bytes=mem_bytes,
            memory_usage_display=self._format_bytes(mem_bytes),
            columns=column_profiles,
            profiled_at=datetime.now(timezone.utc),
            profiling_duration_ms=round(duration_ms, 2),
        )

    # ─── Per-Column Profiling ────────────────────────────────────────

    def _profile_column(
        self,
        series: pd.Series,
        col_name: str,
        position: int,
        total_rows: int,
    ) -> ColumnProfile:
        """Produce a ``ColumnProfile`` for a single column."""
        pandas_dtype = str(series.dtype)

        # Missing values.
        missing_count = int(series.isna().sum())
        missing_pct = (missing_count / total_rows * 100) if total_rows > 0 else 0.0
        completeness = 100.0 - missing_pct

        missing_info = MissingValueInfo(
            count=missing_count,
            percentage=round(missing_pct, 2),
            completeness=round(completeness, 2),
        )

        # Non-null series for further analysis.
        non_null = series.dropna()
        unique_count = int(non_null.nunique())
        uniqueness_ratio = (unique_count / total_rows) if total_rows > 0 else 0.0
        is_unique = unique_count == total_rows and total_rows > 0
        is_constant = unique_count <= 1

        # Semantic type inference.
        semantic_type = self._infer_semantic_type(
            series, non_null, col_name, unique_count, total_rows,
        )

        # Column role.
        role = self._assign_role(semantic_type, col_name)

        # Statistics.
        numeric_stats = None
        categorical_stats = None
        outlier_info = None

        if semantic_type in (SemanticType.NUMERIC_INTEGER, SemanticType.NUMERIC_FLOAT):
            numeric_stats = self._compute_numeric_stats(non_null)
            outlier_info = self._detect_outliers(non_null)
        elif semantic_type in (SemanticType.CATEGORICAL, SemanticType.BOOLEAN):
            categorical_stats = self._compute_categorical_stats(non_null, total_rows)
        elif semantic_type == SemanticType.TEXT:
            # Provide top values even for text columns (useful for quick inspection).
            categorical_stats = self._compute_categorical_stats(non_null, total_rows)

        # Sample values.
        sample_values = self._get_sample_values(non_null, count=5)

        return ColumnProfile(
            name=col_name,
            position=position,
            pandas_dtype=pandas_dtype,
            semantic_type=semantic_type,
            role=role,
            total_count=total_rows,
            unique_count=unique_count,
            uniqueness_ratio=round(uniqueness_ratio, 4),
            is_unique=is_unique,
            is_constant=is_constant,
            missing=missing_info,
            numeric_stats=numeric_stats,
            categorical_stats=categorical_stats,
            outliers=outlier_info,
            sample_values=sample_values,
        )

    # ─── Semantic Type Inference ─────────────────────────────────────

    def _infer_semantic_type(
        self,
        series: pd.Series,
        non_null: pd.Series,
        col_name: str,
        unique_count: int,
        total_rows: int,
    ) -> SemanticType:
        """
        Infer the semantic type of a column using dtype + heuristics.

        Decision tree:

        1. If dtype is datetime → DATETIME.
        2. If dtype is boolean → BOOLEAN.
        3. If dtype is numeric:
           a. If column name matches ID patterns and high cardinality → IDENTIFIER.
           b. Integer vs float → NUMERIC_INTEGER / NUMERIC_FLOAT.
        4. If dtype is object (string):
           a. Try parsing as datetime → DATETIME.
           b. If only 2 unique values → BOOLEAN.
           c. If high cardinality → TEXT or IDENTIFIER (by name pattern).
           d. Otherwise → CATEGORICAL.
        5. Fallback → UNKNOWN.
        """
        dtype = series.dtype
        col_lower = col_name.lower().strip()

        # 1. Native datetime.
        if pd.api.types.is_datetime64_any_dtype(dtype):
            return SemanticType.DATETIME

        # 2. Native boolean.
        if pd.api.types.is_bool_dtype(dtype):
            return SemanticType.BOOLEAN

        # 3. Numeric types.
        if pd.api.types.is_numeric_dtype(dtype):
            # Check if it's an ID column by name.
            if self._matches_id_pattern(col_lower) and total_rows > 0:
                if unique_count / total_rows >= _IDENTIFIER_CARDINALITY_THRESHOLD:
                    return SemanticType.IDENTIFIER

            if pd.api.types.is_integer_dtype(dtype):
                return SemanticType.NUMERIC_INTEGER
            return SemanticType.NUMERIC_FLOAT

        # 4. Object / string types.
        if dtype == object or pd.api.types.is_string_dtype(dtype):
            # 4a. Try datetime parsing (sample-based to avoid slow full-column parse).
            if self._looks_like_datetime(non_null, col_lower):
                return SemanticType.DATETIME

            # 4b. Boolean-like (e.g., "Yes"/"No", "True"/"False").
            if unique_count == 2 and total_rows >= _MIN_ROWS_FOR_CARDINALITY:
                return SemanticType.BOOLEAN

            # 4c. Cardinality-based classification.
            if total_rows >= _MIN_ROWS_FOR_CARDINALITY:
                ratio = unique_count / total_rows

                # ID pattern + high cardinality.
                if self._matches_id_pattern(col_lower) and ratio >= _IDENTIFIER_CARDINALITY_THRESHOLD:
                    return SemanticType.IDENTIFIER

                # High cardinality string → text.
                if ratio >= _TEXT_CARDINALITY_THRESHOLD:
                    return SemanticType.TEXT

            return SemanticType.CATEGORICAL

        # 5. Fallback.
        return SemanticType.UNKNOWN

    # ─── Role Assignment ─────────────────────────────────────────────

    @staticmethod
    def _assign_role(semantic_type: SemanticType, col_name: str) -> ColumnRole:
        """Map a semantic type to an analytical role."""
        role_map: dict[SemanticType, ColumnRole] = {
            SemanticType.NUMERIC_INTEGER: ColumnRole.MEASURE,
            SemanticType.NUMERIC_FLOAT: ColumnRole.MEASURE,
            SemanticType.CATEGORICAL: ColumnRole.DIMENSION,
            SemanticType.BOOLEAN: ColumnRole.DIMENSION,
            SemanticType.DATETIME: ColumnRole.TIME,
            SemanticType.TEXT: ColumnRole.TEXT,
            SemanticType.IDENTIFIER: ColumnRole.IDENTIFIER,
            SemanticType.UNKNOWN: ColumnRole.DIMENSION,
        }
        return role_map.get(semantic_type, ColumnRole.DIMENSION)

    # ─── Numeric Statistics ──────────────────────────────────────────

    @staticmethod
    def _compute_numeric_stats(non_null: pd.Series) -> NumericStats:
        """Compute descriptive statistics for a numeric column."""
        if len(non_null) == 0:
            return NumericStats()

        desc = non_null.describe()

        def _safe_float(val: Any) -> float | None:
            """Convert a value to float, returning None for NaN/Inf."""
            try:
                f = float(val)
                return f if math.isfinite(f) else None
            except (TypeError, ValueError):
                return None

        q1 = _safe_float(desc.get("25%"))
        q3 = _safe_float(desc.get("75%"))
        iqr = (q3 - q1) if (q1 is not None and q3 is not None) else None

        return NumericStats(
            mean=_safe_float(non_null.mean()),
            median=_safe_float(non_null.median()),
            std=_safe_float(non_null.std()),
            min=_safe_float(desc.get("min")),
            max=_safe_float(desc.get("max")),
            q1=q1,
            q3=q3,
            iqr=iqr,
            skewness=_safe_float(non_null.skew()),
            kurtosis=_safe_float(non_null.kurtosis()),
            sum=_safe_float(non_null.sum()),
            zeros_count=int((non_null == 0).sum()),
            negative_count=int((non_null < 0).sum()),
            positive_count=int((non_null > 0).sum()),
        )

    # ─── Categorical Statistics ──────────────────────────────────────

    @staticmethod
    def _compute_categorical_stats(
        non_null: pd.Series,
        total_rows: int,
    ) -> CategoricalStats:
        """Compute frequency statistics for a categorical column."""
        if len(non_null) == 0:
            return CategoricalStats()

        value_counts = non_null.value_counts().head(_MAX_TOP_VALUES)

        top_values = [
            {
                "value": str(val),
                "count": int(cnt),
                "percentage": round(cnt / total_rows * 100, 2) if total_rows > 0 else 0,
            }
            for val, cnt in value_counts.items()
        ]

        mode_val = value_counts.index[0] if len(value_counts) > 0 else None
        mode_freq = int(value_counts.iloc[0]) if len(value_counts) > 0 else 0

        return CategoricalStats(
            top_values=top_values,
            unique_count=int(non_null.nunique()),
            mode=str(mode_val) if mode_val is not None else None,
            mode_frequency=mode_freq,
        )

    # ─── Outlier Detection ───────────────────────────────────────────

    @staticmethod
    def _detect_outliers(non_null: pd.Series) -> OutlierInfo:
        """
        Detect outliers using the IQR (Interquartile Range) method.

        A value is an outlier if it falls below Q1 - 1.5*IQR or above
        Q3 + 1.5*IQR.  This method is robust and non-parametric.
        """
        if len(non_null) < 4:
            return OutlierInfo()

        q1 = float(non_null.quantile(0.25))
        q3 = float(non_null.quantile(0.75))
        iqr = q3 - q1

        if iqr == 0:
            return OutlierInfo(lower_bound=q1, upper_bound=q3)

        lower = q1 - 1.5 * iqr
        upper = q3 + 1.5 * iqr

        outlier_mask = (non_null < lower) | (non_null > upper)
        outlier_count = int(outlier_mask.sum())
        outlier_pct = (outlier_count / len(non_null) * 100) if len(non_null) > 0 else 0.0

        return OutlierInfo(
            method="iqr",
            lower_bound=round(lower, 4),
            upper_bound=round(upper, 4),
            outlier_count=outlier_count,
            outlier_percentage=round(outlier_pct, 2),
        )

    # ─── Helper: Datetime Detection ──────────────────────────────────

    @staticmethod
    def _looks_like_datetime(non_null: pd.Series, col_lower: str) -> bool:
        """
        Heuristic check: does a string column likely contain datetime values?

        Uses a combination of column name pattern matching and sample-based
        parsing to avoid expensive full-column conversion.
        """
        # Name-based hint.
        name_hint = any(
            pattern in col_lower for pattern in _DATETIME_NAME_PATTERNS
        )

        if len(non_null) == 0:
            return name_hint

        # Sample up to 20 non-null values for trial parsing.
        sample = non_null.head(20)
        try:
            with warnings.catch_warnings():
                warnings.simplefilter("ignore", category=UserWarning)
                parsed = pd.to_datetime(sample, errors="coerce")
            success_rate = parsed.notna().sum() / len(sample)
            # Require >80% parse success (or 100% if no name hint).
            threshold = 0.8 if name_hint else 1.0
            return success_rate >= threshold
        except Exception:
            return False

    # ─── Helper: ID Pattern Matching ─────────────────────────────────

    @staticmethod
    def _matches_id_pattern(col_lower: str) -> bool:
        """Check if a column name matches common identifier patterns."""
        # Exact match or suffix/prefix match.
        return any(
            col_lower == pattern
            or col_lower.endswith(f"_{pattern}")
            or col_lower.startswith(f"{pattern}_")
            or col_lower.endswith(pattern)
            for pattern in _ID_NAME_PATTERNS
        )

    # ─── Helper: Sample Values ───────────────────────────────────────

    @staticmethod
    def _get_sample_values(non_null: pd.Series, count: int = 5) -> list[Any]:
        """Extract up to ``count`` non-null sample values, JSON-safe."""
        if len(non_null) == 0:
            return []

        samples = non_null.head(count).tolist()
        safe: list[Any] = []
        for val in samples:
            if isinstance(val, (np.integer,)):
                safe.append(int(val))
            elif isinstance(val, (np.floating,)):
                f = float(val)
                safe.append(f if math.isfinite(f) else None)
            elif isinstance(val, (np.bool_,)):
                safe.append(bool(val))
            elif isinstance(val, pd.Timestamp):
                safe.append(val.isoformat())
            else:
                safe.append(str(val))
        return safe

    # ─── Helper: Byte Formatting ─────────────────────────────────────

    @staticmethod
    def _format_bytes(size: int) -> str:
        """Convert bytes to human-readable string."""
        for unit in ("B", "KB", "MB", "GB"):
            if abs(size) < 1024:
                return f"{size:.1f} {unit}"
            size /= 1024  # type: ignore[assignment]
        return f"{size:.1f} TB"


# ─── Module-level Singleton ──────────────────────────────────────────────────

_profiling_service: ProfilingService | None = None


def get_profiling_service() -> ProfilingService:
    """Return the module-level ``ProfilingService`` singleton."""
    global _profiling_service
    if _profiling_service is None:
        _profiling_service = ProfilingService()
    return _profiling_service
