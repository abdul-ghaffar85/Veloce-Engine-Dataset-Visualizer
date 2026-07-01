# ═══════════════════════════════════════════════════════════════════════════════
# Veloce Engine — Report Builder Schemas
# ═══════════════════════════════════════════════════════════════════════════════
"""
Pydantic v2 schemas for the Report Builder Engine.

Defines the payload for exporting raw or dynamically queried datasets
to standard business formats like CSV and Excel.
"""

from __future__ import annotations

import enum

from pydantic import BaseModel, Field

from backend.schemas.aggregation import QueryRequest


# ═══════════════════════════════════════════════════════════════════════════════
# Enums
# ═══════════════════════════════════════════════════════════════════════════════

class ExportFormat(str, enum.Enum):
    """Supported export file formats."""
    CSV = "csv"
    EXCEL = "excel"


# ═══════════════════════════════════════════════════════════════════════════════
# Export Request
# ═══════════════════════════════════════════════════════════════════════════════

class ExportRequest(BaseModel):
    """
    Request payload to export a dataset.
    
    If `query` is provided, the data will be filtered, grouped, and sorted
    according to the query before being exported. Pagination limits in the query
    are automatically overridden to allow full dataset exports.
    """
    format: ExportFormat = Field(default=ExportFormat.CSV, description="Target file format.")
    file_name: str | None = Field(default=None, description="Optional custom filename. Extension appended automatically if missing.")
    query: QueryRequest | None = Field(default=None, description="Optional aggregation query to apply before exporting.")
