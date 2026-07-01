# ═══════════════════════════════════════════════════════════════════════════════
# Veloce Engine — Relationship Schemas
# ═══════════════════════════════════════════════════════════════════════════════
"""
Pydantic v2 response schemas for the Relationship Discovery Engine.

These models define the internal and external formats for dataset relationships,
correlations, key candidates, and cross-dataset joins.
"""

from __future__ import annotations

import enum
from typing import Any

from pydantic import BaseModel, Field


# ═══════════════════════════════════════════════════════════════════════════════
# Enums
# ═══════════════════════════════════════════════════════════════════════════════

class JoinType(str, enum.Enum):
    """Cardinality of a cross-dataset relationship."""
    ONE_TO_ONE = "1:1"
    ONE_TO_MANY = "1:N"
    MANY_TO_ONE = "N:1"
    MANY_TO_MANY = "M:N"


# ═══════════════════════════════════════════════════════════════════════════════
# Single Dataset Relationships
# ═══════════════════════════════════════════════════════════════════════════════

class CorrelationResult(BaseModel):
    """Correlation between two numeric columns."""
    column_a: str
    column_b: str
    pearson: float | None = Field(default=None, description="Pearson correlation coefficient.")
    spearman: float | None = Field(default=None, description="Spearman rank correlation coefficient.")


class PrimaryKeyCandidate(BaseModel):
    """A candidate primary key (single or composite)."""
    columns: list[str] = Field(description="List of column names forming the key.")
    is_composite: bool = Field(description="True if the key consists of multiple columns.")
    uniqueness_ratio: float = Field(description="Ratio of unique values to total rows (0.0 to 1.0).")


class FunctionalDependency(BaseModel):
    """A detected functional dependency (A -> B)."""
    determinant: str = Field(description="The column(s) that determine the dependent column.")
    dependent: str = Field(description="The column that is determined.")
    strength: float = Field(description="Strength of dependency (1.0 = strict).")


class SingleDatasetRelationships(BaseModel):
    """All discovered relationships within a single dataset."""
    dataset_id: str
    correlations: list[CorrelationResult] = Field(default_factory=list)
    primary_key_candidates: list[PrimaryKeyCandidate] = Field(default_factory=list)
    functional_dependencies: list[FunctionalDependency] = Field(default_factory=list)


class SingleDatasetRelationshipResponse(BaseModel):
    """API response wrapper for single dataset relationships."""
    status: str = "success"
    relationships: SingleDatasetRelationships


# ═══════════════════════════════════════════════════════════════════════════════
# Multi-Dataset Relationships (Graph)
# ═══════════════════════════════════════════════════════════════════════════════

class CrossDatasetRelationship(BaseModel):
    """A discovered relationship (join candidate) between two datasets."""
    source_dataset_id: str
    source_columns: list[str]
    target_dataset_id: str
    target_columns: list[str]
    match_percentage: float = Field(description="Percentage of source keys found in target dataset.")
    join_type: JoinType = Field(description="Detected cardinality (e.g., 1:N).")
    confidence_score: float = Field(description="Overall confidence in this join (0.0 to 1.0).")


class RelationshipGraph(BaseModel):
    """The complete internal graph of dataset relationships."""
    datasets: list[str] = Field(description="List of dataset IDs in the graph.")
    relationships: list[CrossDatasetRelationship] = Field(default_factory=list)


class MultiDatasetRelationshipResponse(BaseModel):
    """API response wrapper for multi-dataset relationship graph."""
    status: str = "success"
    graph: RelationshipGraph
