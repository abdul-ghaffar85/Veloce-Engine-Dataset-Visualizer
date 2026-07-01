# ═══════════════════════════════════════════════════════════════════════════════
# Veloce Engine — Dataset Schemas
# ═══════════════════════════════════════════════════════════════════════════════
"""
Pydantic v2 response schemas for the Dataset Upload API.

These models define the wire format for all dataset-related endpoints.
They are separate from internal models (``DatasetMetadata``) to allow
the API contract to evolve independently of internal state.
"""

from __future__ import annotations

from datetime import datetime
from typing import Any

from pydantic import BaseModel, Field


# ═══════════════════════════════════════════════════════════════════════════════
# Single Dataset Response
# ═══════════════════════════════════════════════════════════════════════════════

class DatasetResponse(BaseModel):
    """API response for a single uploaded dataset."""

    dataset_id: str = Field(description="Unique dataset identifier.")
    original_filename: str = Field(description="Original user-supplied filename.")
    file_type: str = Field(description="Detected file type (csv, xlsx, xls).")
    size_bytes: int = Field(description="File size in bytes.")
    size_display: str = Field(description="Human-readable file size.")
    encoding: str | None = Field(default=None, description="Character encoding (CSV only).")
    row_count: int | None = Field(default=None, description="Number of data rows.")
    column_count: int | None = Field(default=None, description="Number of columns.")
    columns: list[str] = Field(default_factory=list, description="Column names.")
    has_formula_warnings: bool = Field(default=False, description="Formula injection detected.")
    formula_warning_count: int = Field(default=0, description="Number of flagged cells.")
    uploaded_at: datetime = Field(description="Upload timestamp (UTC).")

    @staticmethod
    def format_size(size_bytes: int) -> str:
        """Convert bytes to human-readable string."""
        for unit in ("B", "KB", "MB", "GB"):
            if abs(size_bytes) < 1024:
                return f"{size_bytes:.1f} {unit}"
            size_bytes /= 1024  # type: ignore[assignment]
        return f"{size_bytes:.1f} TB"


# ═══════════════════════════════════════════════════════════════════════════════
# Upload Response (wraps dataset + upload status)
# ═══════════════════════════════════════════════════════════════════════════════

class UploadResponse(BaseModel):
    """Response for a successful single-file upload."""

    status: str = "success"
    message: str = "Dataset uploaded successfully."
    dataset: DatasetResponse


# ═══════════════════════════════════════════════════════════════════════════════
# Batch Upload Response
# ═══════════════════════════════════════════════════════════════════════════════

class BatchUploadResult(BaseModel):
    """Result for one file in a batch upload."""

    filename: str
    status: str  # "success" | "error"
    dataset: DatasetResponse | None = None
    error: str | None = None


class BatchUploadResponse(BaseModel):
    """Response for a batch (multi-file) upload."""

    status: str = "completed"
    total: int = Field(description="Total files submitted.")
    succeeded: int = Field(description="Number of files uploaded successfully.")
    failed: int = Field(description="Number of files that failed.")
    results: list[BatchUploadResult]


# ═══════════════════════════════════════════════════════════════════════════════
# Dataset List Response
# ═══════════════════════════════════════════════════════════════════════════════

class DatasetListResponse(BaseModel):
    """Response for listing all uploaded datasets."""

    status: str = "success"
    count: int = Field(description="Number of datasets.")
    datasets: list[DatasetResponse]


# ═══════════════════════════════════════════════════════════════════════════════
# Preview Response
# ═══════════════════════════════════════════════════════════════════════════════

class PreviewResponse(BaseModel):
    """Response for dataset row preview."""

    status: str = "success"
    dataset_id: str
    columns: list[str] = Field(description="Column names.")
    data: list[dict[str, Any]] = Field(description="Row data (list of dicts).")
    total_rows: int | None = Field(description="Total rows in the dataset.")
    preview_rows: int = Field(description="Number of rows returned.")


# ═══════════════════════════════════════════════════════════════════════════════
# Delete Response
# ═══════════════════════════════════════════════════════════════════════════════

class DeleteResponse(BaseModel):
    """Response for dataset deletion."""

    status: str = "success"
    message: str = "Dataset deleted successfully."
    dataset_id: str
