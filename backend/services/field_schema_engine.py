# ═══════════════════════════════════════════════════════════════════════════════
# Veloce Engine — Field Schema Engine (XLBooster-Style Metadata)
# ═══════════════════════════════════════════════════════════════════════════════
"""
Orchestration layer that merges Profiling + Semantic AI results into
unified ``FieldDescriptor`` objects for the interactive analytics UI.

This engine does **not** duplicate analysis logic.  It calls the existing
:class:`~backend.services.profiler.ProfilingService` and
:class:`~backend.services.semantic_engine.SemanticEngineService`, then
transforms their output into the shape required by the drag-and-drop
frontend.

Usage::

    from backend.services.field_schema_engine import get_field_schema_engine

    engine = get_field_schema_engine()
    schema = await engine.build_schema(dataset_id, filename, df)
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
from backend.schemas.field_schema import (
    DatasetFieldSchema,
    FieldDataType,
    FieldDescriptor,
    FieldSemanticType,
    FieldStatistics,
)
from backend.schemas.profile import ColumnProfile, ColumnRole, SemanticType
from backend.schemas.semantic import BusinessEntity, ColumnSemanticProfile
from backend.services.profiler import get_profiling_service
from backend.services.semantic_engine import get_semantic_engine

_logger = get_logger(__name__)

# ─── Constants ───────────────────────────────────────────────────────────────

_MAX_UNIQUE_VALUES_FOR_LIST = 50
_SAMPLE_SIZE_FOR_PRECISION = 100
_DEFAULT_DATE_HIERARCHY = ["year", "quarter", "month", "week", "day"]

# Aggregation suggestions per semantic type
_AGGREGATION_MAP: dict[FieldSemanticType, list[str]] = {
    FieldSemanticType.METRIC: ["sum", "mean", "median", "min", "max", "count"],
    FieldSemanticType.DIMENSION: ["count", "nunique"],
    FieldSemanticType.TIME: ["min", "max", "count"],
    FieldSemanticType.IDENTIFIER: ["count", "nunique"],
    FieldSemanticType.TEXT: ["count", "nunique"],
}

# Default aggregation per semantic type
_DEFAULT_AGG_MAP: dict[FieldSemanticType, str] = {
    FieldSemanticType.METRIC: "sum",
    FieldSemanticType.DIMENSION: "count",
    FieldSemanticType.TIME: "count",
    FieldSemanticType.IDENTIFIER: "count",
    FieldSemanticType.TEXT: "count",
}


# ═══════════════════════════════════════════════════════════════════════════════
# Column Role → Field Semantic Type mapping
# ═══════════════════════════════════════════════════════════════════════════════

def _role_to_semantic_type(role: ColumnRole) -> FieldSemanticType:
    """Map the profiler's ColumnRole to the field schema's FieldSemanticType."""
    mapping = {
        ColumnRole.DIMENSION: FieldSemanticType.DIMENSION,
        ColumnRole.MEASURE: FieldSemanticType.METRIC,
        ColumnRole.TIME: FieldSemanticType.TIME,
        ColumnRole.IDENTIFIER: FieldSemanticType.IDENTIFIER,
        ColumnRole.TEXT: FieldSemanticType.TEXT,
    }
    return mapping.get(role, FieldSemanticType.DIMENSION)


# ═══════════════════════════════════════════════════════════════════════════════
# Semantic Type → Field Data Type mapping
# ═══════════════════════════════════════════════════════════════════════════════

def _semantic_to_data_type(sem_type: SemanticType) -> FieldDataType:
    """Map the profiler's SemanticType to a simplified FieldDataType."""
    mapping = {
        SemanticType.NUMERIC_INTEGER: FieldDataType.INTEGER,
        SemanticType.NUMERIC_FLOAT: FieldDataType.FLOAT,
        SemanticType.CATEGORICAL: FieldDataType.STRING,
        SemanticType.BOOLEAN: FieldDataType.BOOLEAN,
        SemanticType.DATETIME: FieldDataType.DATETIME,
        SemanticType.TEXT: FieldDataType.STRING,
        SemanticType.IDENTIFIER: FieldDataType.STRING,
        SemanticType.UNKNOWN: FieldDataType.STRING,
    }
    return mapping.get(sem_type, FieldDataType.STRING)


# ═══════════════════════════════════════════════════════════════════════════════
# Field Schema Engine
# ═══════════════════════════════════════════════════════════════════════════════

class FieldSchemaEngine:
    """
    Builds unified field descriptors by composing the existing Profiling
    and Semantic AI engines.

    All heavy computation is delegated to those engines (which already
    run in thread pools).  This class only performs lightweight
    transformation and merging.
    """

    async def build_schema(
        self,
        dataset_id: str,
        filename: str,
        df: pd.DataFrame,
    ) -> DatasetFieldSchema:
        """
        Build the complete field schema for a dataset.

        1. Run the profiler to get column types, roles, and statistics.
        2. Run the semantic engine to get business entity classifications.
        3. Merge both into FieldDescriptor objects.
        4. Enrich with aggregation suggestions, date hierarchies, etc.

        Args:
            dataset_id: Unique dataset identifier.
            filename:   Display name for the dataset.
            df:         The pandas DataFrame to analyse.

        Returns:
            A ``DatasetFieldSchema`` with all field descriptors.
        """
        start = time.perf_counter()

        try:
            # Run profiling and semantic analysis concurrently
            profiler = get_profiling_service()
            semantic_engine = get_semantic_engine()

            profile_result, semantic_result = await asyncio.gather(
                profiler.profile_dataset(
                    dataset_id=dataset_id,
                    filename=filename,
                    df=df,
                ),
                semantic_engine.analyze_dataset(dataset_id, df),
            )
        except Exception as exc:
            _logger.exception(
                "field_schema_analysis_failed",
                dataset_id=dataset_id,
                error=str(exc),
            )
            raise DataProcessingError(
                message="Failed to build field schema for dataset.",
                internal=str(exc),
            ) from exc

        # Build a lookup for semantic results by column name
        semantic_lookup: dict[str, ColumnSemanticProfile] = {
            col.column_name: col for col in semantic_result.columns
        }

        # Transform each profiled column into a FieldDescriptor
        fields: list[FieldDescriptor] = []
        for col_profile in profile_result.columns:
            sem_profile = semantic_lookup.get(col_profile.name)
            field = await asyncio.to_thread(
                self._build_field_descriptor,
                col_profile,
                sem_profile,
                df,
            )
            fields.append(field)

        # Count by type
        dim_count = sum(
            1 for f in fields
            if f.semanticType in (FieldSemanticType.DIMENSION, FieldSemanticType.TEXT)
        )
        metric_count = sum(
            1 for f in fields if f.semanticType == FieldSemanticType.METRIC
        )
        time_count = sum(
            1 for f in fields if f.semanticType == FieldSemanticType.TIME
        )

        duration_ms = (time.perf_counter() - start) * 1000

        _logger.info(
            "field_schema_built",
            dataset_id=dataset_id,
            fields=len(fields),
            dimensions=dim_count,
            metrics=metric_count,
            time_fields=time_count,
            duration_ms=round(duration_ms, 2),
        )

        return DatasetFieldSchema(
            dataset_id=dataset_id,
            filename=filename,
            row_count=len(df),
            column_count=len(df.columns),
            fields=fields,
            dimension_count=dim_count,
            metric_count=metric_count,
            time_count=time_count,
        )

    # ─── Private: Build a Single FieldDescriptor ─────────────────────

    def _build_field_descriptor(
        self,
        col_profile: ColumnProfile,
        sem_profile: ColumnSemanticProfile | None,
        df: pd.DataFrame,
    ) -> FieldDescriptor:
        """
        Merge a ColumnProfile and ColumnSemanticProfile into a
        FieldDescriptor.  Runs synchronously (called via to_thread).
        """
        semantic_type = _role_to_semantic_type(col_profile.role)
        data_type = _semantic_to_data_type(col_profile.semantic_type)

        # Business entity from semantic engine
        business_entity: str | None = None
        if sem_profile and sem_profile.entity_type != BusinessEntity.UNKNOWN:
            business_entity = sem_profile.entity_type.value

        # Nullable
        nullable = col_profile.missing.count > 0

        # Aggregation suggestions
        aggregations = list(_AGGREGATION_MAP.get(semantic_type, ["count"]))
        default_agg = _DEFAULT_AGG_MAP.get(semantic_type, "count")

        # Unique values list (only for low-cardinality dimensions)
        unique_values: list[Any] | None = None
        if (
            semantic_type in (FieldSemanticType.DIMENSION, FieldSemanticType.TIME)
            and col_profile.unique_count <= _MAX_UNIQUE_VALUES_FOR_LIST
            and col_profile.name in df.columns
        ):
            raw_unique = df[col_profile.name].dropna().unique()
            unique_values = self._safe_serialize_list(raw_unique.tolist())

        # Date hierarchy (for time fields)
        date_hierarchy: list[str] | None = None
        if semantic_type == FieldSemanticType.TIME:
            date_hierarchy = list(_DEFAULT_DATE_HIERARCHY)

        # Numeric precision (for float fields)
        numeric_precision: int | None = None
        if data_type == FieldDataType.FLOAT and col_profile.name in df.columns:
            numeric_precision = self._detect_precision(df[col_profile.name])

        # Statistics
        statistics = self._build_statistics(col_profile)

        return FieldDescriptor(
            field=col_profile.name,
            position=col_profile.position,
            semanticType=semantic_type,
            dataType=data_type,
            businessEntity=business_entity,
            nullable=nullable,
            cardinality=col_profile.unique_count,
            uniquenessRatio=col_profile.uniqueness_ratio,
            isUnique=col_profile.is_unique,
            isConstant=col_profile.is_constant,
            aggregations=aggregations,
            defaultAggregation=default_agg,
            sampleValues=col_profile.sample_values,
            uniqueValues=unique_values,
            dateHierarchy=date_hierarchy,
            numericPrecision=numeric_precision,
            statistics=statistics,
        )

    # ─── Private: Build Statistics ───────────────────────────────────

    @staticmethod
    def _build_statistics(col_profile: ColumnProfile) -> FieldStatistics:
        """Extract compact statistics from a ColumnProfile."""
        stats = FieldStatistics(
            missing_count=col_profile.missing.count,
            missing_percentage=col_profile.missing.percentage,
            completeness=col_profile.missing.completeness,
        )

        if col_profile.numeric_stats is not None:
            ns = col_profile.numeric_stats
            stats.min = ns.min
            stats.max = ns.max
            stats.mean = ns.mean
            stats.median = ns.median
            stats.sum = ns.sum
            stats.std = ns.std

        if col_profile.outliers is not None:
            stats.outlier_count = col_profile.outliers.outlier_count
            stats.outlier_percentage = col_profile.outliers.outlier_percentage

        if col_profile.categorical_stats is not None:
            cs = col_profile.categorical_stats
            stats.mode = cs.mode
            stats.top_values = cs.top_values[:10]  # Cap at 10 for the field schema

        return stats

    # ─── Private: Detect Numeric Precision ───────────────────────────

    @staticmethod
    def _detect_precision(series: pd.Series) -> int:
        """
        Determine the typical number of decimal places in a float column.

        Samples up to 100 non-null values and finds the maximum number
        of decimal digits observed.
        """
        non_null = series.dropna()
        if len(non_null) == 0:
            return 2  # Default

        sample = non_null.head(_SAMPLE_SIZE_FOR_PRECISION)
        max_precision = 0

        for val in sample:
            try:
                f = float(val)
                if not math.isfinite(f):
                    continue
                s = f"{f:.10f}".rstrip("0")
                if "." in s:
                    decimal_part = s.split(".")[1]
                    max_precision = max(max_precision, len(decimal_part))
            except (TypeError, ValueError):
                continue

        return min(max_precision, 6)  # Cap at 6

    # ─── Private: Safe Serialization ─────────────────────────────────

    @staticmethod
    def _safe_serialize_list(values: list[Any]) -> list[Any]:
        """Convert numpy/pandas types to JSON-safe Python types."""
        safe: list[Any] = []
        for val in values:
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


# ─── Module-level Singleton ──────────────────────────────────────────────────

_field_schema_engine: FieldSchemaEngine | None = None


def get_field_schema_engine() -> FieldSchemaEngine:
    """Return the module-level ``FieldSchemaEngine`` singleton."""
    global _field_schema_engine
    if _field_schema_engine is None:
        _field_schema_engine = FieldSchemaEngine()
    return _field_schema_engine
