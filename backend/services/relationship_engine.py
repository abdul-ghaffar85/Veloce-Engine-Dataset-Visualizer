# ═══════════════════════════════════════════════════════════════════════════════
# Veloce Engine — Relationship Discovery Engine
# ═══════════════════════════════════════════════════════════════════════════════
"""
Automatic relationship discovery service.

Analyzes datasets to infer correlations, functional dependencies, primary key
candidates, and cross-dataset join relationships without manual configuration.
All heavy computation is offloaded to a thread pool.

Usage::

    from backend.services.relationship_engine import get_relationship_engine

    engine = get_relationship_engine()
    single_rel = await engine.analyze_single_dataset(dataset_id, df)
    graph = await engine.build_relationship_graph(datasets_dict)
"""

from __future__ import annotations

import asyncio
import itertools
import math
from typing import Any

import numpy as np
import pandas as pd

from backend.core.exceptions import RelationshipDiscoveryError
from backend.core.logging import get_logger
from backend.schemas.relationship import (
    CorrelationResult,
    CrossDatasetRelationship,
    FunctionalDependency,
    JoinType,
    PrimaryKeyCandidate,
    RelationshipGraph,
    SingleDatasetRelationships,
)

_logger = get_logger(__name__)


# ─── Heuristic Thresholds ────────────────────────────────────────────────────

_PK_UNIQUENESS_THRESHOLD = 0.99
_FD_STRENGTH_THRESHOLD = 0.95
_MIN_CORRELATION_THRESHOLD = 0.1
_MIN_JOIN_MATCH_PERCENTAGE = 0.1
_MAX_JOIN_SAMPLE_SIZE = 10_000


# ═══════════════════════════════════════════════════════════════════════════════
# Relationship Engine Service
# ═══════════════════════════════════════════════════════════════════════════════

class RelationshipEngineService:
    """
    Stateless relationship discovery service.
    Executes Pandas/NumPy operations in a thread pool.
    """

    async def analyze_single_dataset(
        self,
        dataset_id: str,
        df: pd.DataFrame,
    ) -> SingleDatasetRelationships:
        """
        Analyze a single dataset for correlations, PKs, and FDs.
        """
        try:
            return await asyncio.to_thread(self._analyze_single_sync, dataset_id, df)
        except Exception as exc:
            _logger.exception("single_dataset_analysis_failed", dataset_id=dataset_id, error=str(exc))
            raise RelationshipDiscoveryError(
                message="Failed to analyze dataset relationships.",
                internal=str(exc),
            ) from exc

    async def build_relationship_graph(
        self,
        datasets: dict[str, pd.DataFrame],
    ) -> RelationshipGraph:
        """
        Discover cross-dataset relationships (foreign keys, join paths).
        """
        try:
            return await asyncio.to_thread(self._build_graph_sync, datasets)
        except Exception as exc:
            _logger.exception("graph_build_failed", error=str(exc))
            raise RelationshipDiscoveryError(
                message="Failed to build relationship graph.",
                internal=str(exc),
            ) from exc

    # ─── Synchronous Implementations ─────────────────────────────────

    def _analyze_single_sync(
        self,
        dataset_id: str,
        df: pd.DataFrame,
    ) -> SingleDatasetRelationships:
        _logger.info("single_dataset_analysis_started", dataset_id=dataset_id)

        correlations = self._compute_correlations(df)
        pk_candidates = self._find_primary_keys(df)
        fds = self._find_functional_dependencies(df)

        return SingleDatasetRelationships(
            dataset_id=dataset_id,
            correlations=correlations,
            primary_key_candidates=pk_candidates,
            functional_dependencies=fds,
        )

    def _build_graph_sync(
        self,
        datasets: dict[str, pd.DataFrame],
    ) -> RelationshipGraph:
        _logger.info("graph_build_started", dataset_count=len(datasets))

        dataset_ids = list(datasets.keys())
        relationships: list[CrossDatasetRelationship] = []

        # Compare every pair of datasets
        for source_id, target_id in itertools.combinations(dataset_ids, 2):
            source_df = datasets[source_id]
            target_df = datasets[target_id]

            # Bi-directional check
            rels = self._find_join_candidates(source_id, source_df, target_id, target_df)
            relationships.extend(rels)

        return RelationshipGraph(
            datasets=dataset_ids,
            relationships=relationships,
        )

    # ─── Internal Analysis Methods ───────────────────────────────────

    def _compute_correlations(self, df: pd.DataFrame) -> list[CorrelationResult]:
        numeric_df = df.select_dtypes(include=[np.number])
        if numeric_df.empty or len(numeric_df.columns) < 2:
            return []

        # Compute Pearson and Spearman matrices
        pearson_mat = numeric_df.corr(method="pearson")
        spearman_mat = numeric_df.corr(method="spearman")

        results = []
        cols = pearson_mat.columns
        for i in range(len(cols)):
            for j in range(i + 1, len(cols)):
                col_a = cols[i]
                col_b = cols[j]
                
                p_val = pearson_mat.iloc[i, j]
                s_val = spearman_mat.iloc[i, j]

                if pd.isna(p_val):
                    p_val = None
                if pd.isna(s_val):
                    s_val = None

                # Only include significant correlations
                if (p_val and abs(p_val) >= _MIN_CORRELATION_THRESHOLD) or (s_val and abs(s_val) >= _MIN_CORRELATION_THRESHOLD):
                    results.append(
                        CorrelationResult(
                            column_a=col_a,
                            column_b=col_b,
                            pearson=float(p_val) if p_val is not None else None,
                            spearman=float(s_val) if s_val is not None else None,
                        )
                    )

        return results

    def _find_primary_keys(self, df: pd.DataFrame) -> list[PrimaryKeyCandidate]:
        candidates = []
        total_rows = len(df)
        if total_rows == 0:
            return candidates

        # Single column PKs
        for col in df.columns:
            # Skip floating point columns as keys
            if pd.api.types.is_float_dtype(df[col]):
                continue

            unique_count = df[col].nunique()
            ratio = unique_count / total_rows

            if ratio >= _PK_UNIQUENESS_THRESHOLD:
                candidates.append(
                    PrimaryKeyCandidate(
                        columns=[col],
                        is_composite=False,
                        uniqueness_ratio=round(ratio, 4),
                    )
                )

        # Composite PKs (heuristic: check pairs of categorical/id-like columns)
        # To avoid combinatorial explosion, only test if no single column is a perfect PK
        if not any(c.uniqueness_ratio == 1.0 for c in candidates):
            candidate_cols = [col for col in df.columns if not pd.api.types.is_float_dtype(df[col]) and df[col].nunique() < total_rows]
            # Limit to a small number of columns for composite key search
            if len(candidate_cols) <= 10:
                for col_a, col_b in itertools.combinations(candidate_cols, 2):
                    unique_count = df[[col_a, col_b]].drop_duplicates().shape[0]
                    ratio = unique_count / total_rows
                    if ratio >= _PK_UNIQUENESS_THRESHOLD:
                        candidates.append(
                            PrimaryKeyCandidate(
                                columns=[col_a, col_b],
                                is_composite=True,
                                uniqueness_ratio=round(ratio, 4),
                            )
                        )

        # Sort by uniqueness desc, then length of columns asc
        candidates.sort(key=lambda x: (-x.uniqueness_ratio, len(x.columns)))
        return candidates

    def _find_functional_dependencies(self, df: pd.DataFrame) -> list[FunctionalDependency]:
        """
        Heuristic detection of A -> B dependencies.
        If unique values of A uniquely determine B, then grouping by A should
        yield 1 unique value of B per group.
        """
        dependencies = []
        total_rows = len(df)
        if total_rows == 0:
            return dependencies

        # Limit to low/medium cardinality columns to avoid massive compute
        candidate_cols = [col for col in df.columns if 1 < df[col].nunique() < (total_rows * 0.5)]

        for col_a, col_b in itertools.permutations(candidate_cols, 2):
            if col_a == col_b:
                continue

            # Drop nulls for checking
            subset = df[[col_a, col_b]].dropna()
            if len(subset) == 0:
                continue

            # Check if each A has exactly one B
            unique_a = subset[col_a].nunique()
            unique_ab = subset[[col_a, col_b]].drop_duplicates().shape[0]

            # Strength: how close is unique_ab to unique_a?
            # 1.0 means perfect functional dependency
            strength = unique_a / unique_ab if unique_ab > 0 else 0

            if strength >= _FD_STRENGTH_THRESHOLD:
                dependencies.append(
                    FunctionalDependency(
                        determinant=col_a,
                        dependent=col_b,
                        strength=round(strength, 4),
                    )
                )

        return dependencies

    def _find_join_candidates(
        self,
        source_id: str,
        source_df: pd.DataFrame,
        target_id: str,
        target_df: pd.DataFrame,
    ) -> list[CrossDatasetRelationship]:
        """Identify potential join relationships between two datasets."""
        rels = []

        # Find columns with similar names or likely ID roles
        source_cols = set(source_df.columns)
        target_cols = set(target_df.columns)

        # Common column names are strong candidates
        common_cols = source_cols.intersection(target_cols)

        # We also check pairs where names contain "id" or match partially
        # (e.g. "customer_id" in A, "id" in B)
        candidates = []
        for s_col in source_cols:
            for t_col in target_cols:
                # Same name
                if s_col == t_col:
                    candidates.append((s_col, t_col))
                # ID matching heuristics
                elif "id" in s_col.lower() and "id" in t_col.lower():
                    candidates.append((s_col, t_col))

        # Test candidates
        tested = set()
        for s_col, t_col in candidates:
            if (s_col, t_col) in tested:
                continue
            tested.add((s_col, t_col))

            # Skip wildly incompatible types
            if source_df[s_col].dtype.kind != target_df[t_col].dtype.kind:
                # String vs Numeric could be an ID, but usually signals a mismatch. 
                # Let's allow object/string matching with numeric if they parse
                pass

            s_series = source_df[s_col].dropna().astype(str)
            t_series = target_df[t_col].dropna().astype(str)

            if len(s_series) == 0 or len(t_series) == 0:
                continue

            # Subsample for large datasets to speed up intersection checks
            s_sample = set(s_series.sample(min(len(s_series), _MAX_JOIN_SAMPLE_SIZE)))
            t_sample = set(t_series.sample(min(len(t_series), _MAX_JOIN_SAMPLE_SIZE)))

            intersection = s_sample.intersection(t_sample)
            if not intersection:
                continue

            s_match_pct = len(intersection) / len(s_sample)
            t_match_pct = len(intersection) / len(t_sample)

            # We consider it a join if either direction has significant overlap
            if s_match_pct >= _MIN_JOIN_MATCH_PERCENTAGE or t_match_pct >= _MIN_JOIN_MATCH_PERCENTAGE:
                
                # Determine Join Type based on uniqueness of the original series
                s_unique = source_df[s_col].is_unique
                t_unique = target_df[t_col].is_unique

                if s_unique and t_unique:
                    join_type = JoinType.ONE_TO_ONE
                elif s_unique and not t_unique:
                    join_type = JoinType.ONE_TO_MANY
                elif not s_unique and t_unique:
                    join_type = JoinType.MANY_TO_ONE
                else:
                    join_type = JoinType.MANY_TO_MANY

                # Confidence heuristic
                confidence = (s_match_pct + t_match_pct) / 2.0
                
                # Boost confidence if column names match exactly
                if s_col == t_col:
                    confidence = min(1.0, confidence + 0.2)

                rels.append(
                    CrossDatasetRelationship(
                        source_dataset_id=source_id,
                        source_columns=[s_col],
                        target_dataset_id=target_id,
                        target_columns=[t_col],
                        match_percentage=round(max(s_match_pct, t_match_pct), 4),
                        join_type=join_type,
                        confidence_score=round(confidence, 4),
                    )
                )

        return rels


# ─── Module-level Singleton ──────────────────────────────────────────────────

_relationship_engine: RelationshipEngineService | None = None

def get_relationship_engine() -> RelationshipEngineService:
    global _relationship_engine
    if _relationship_engine is None:
        _relationship_engine = RelationshipEngineService()
    return _relationship_engine
