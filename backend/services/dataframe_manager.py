# ═══════════════════════════════════════════════════════════════════════════════
# Veloce Engine — DataFrame Manager
# ═══════════════════════════════════════════════════════════════════════════════
"""
In-memory dataset manager for uploaded CSV and Excel files.

Responsibilities:

* Load validated uploads into Pandas DataFrames.
* Assign stable dataset IDs.
* Hold active datasets in memory for the current session.
* Return metadata and DataFrames by ID.
* Provide previews, listing, and deletion.

The manager intentionally avoids database persistence. Uploaded content lives
only in memory for the lifetime of the process.
"""

from __future__ import annotations

import asyncio
import io
import threading
import uuid
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Any

import pandas as pd
from pydantic import BaseModel, Field

from backend.core.exceptions import DataProcessingError, DatasetNotFoundError, FileUploadError
from backend.core.logging import get_logger
from backend.services.file_validator import FileType, ValidationResult

_logger = get_logger(__name__)


class DatasetMetadata(BaseModel):
    """Metadata for an uploaded dataset held in memory."""

    dataset_id: str = Field(description="Unique dataset identifier.")
    original_filename: str = Field(description="Original user-supplied filename.")
    sanitised_filename: str = Field(description="Sanitised filename.")
    file_type: FileType = Field(description="Detected file type.")
    content_type: str = Field(description="Declared MIME content type.")
    size_bytes: int = Field(description="Uploaded file size in bytes.")
    encoding: str | None = Field(default=None, description="CSV encoding if detected.")
    row_count: int | None = Field(default=None, description="Number of rows in the DataFrame.")
    column_count: int | None = Field(default=None, description="Number of columns in the DataFrame.")
    columns: list[str] = Field(default_factory=list, description="Column names.")
    has_formula_warnings: bool = Field(default=False, description="Whether formula injection was detected.")
    formula_warning_count: int = Field(default=0, description="Formula warning count.")
    uploaded_at: datetime = Field(description="UTC upload timestamp.")

    model_config = {"frozen": True}


@dataclass(slots=True)
class DatasetRecord:
    """Internal in-memory dataset bundle."""

    metadata: DatasetMetadata
    dataframe: pd.DataFrame


class DataFrameManager:
    """Owns uploaded DataFrames and their metadata in memory."""

    def __init__(self) -> None:
        self._records: dict[str, DatasetRecord] = {}
        self._lock = threading.RLock()

    async def register_upload(self, validation: ValidationResult) -> DatasetMetadata:
        """Load a validated upload into memory and return its metadata."""
        try:
            return await asyncio.to_thread(self._register_upload_sync, validation)
        except DataProcessingError:
            raise
        except Exception as exc:
            _logger.exception("dataset_registration_failed", filename=validation.original_filename, error=str(exc))
            raise DataProcessingError(
                message="Failed to load the uploaded dataset into memory.",
                internal=str(exc),
            ) from exc

    def get_record(self, dataset_id: str) -> DatasetRecord:
        """Return the in-memory record for a dataset ID."""
        with self._lock:
            record = self._records.get(dataset_id)
        if record is None:
            raise DatasetNotFoundError(dataset_id=dataset_id)
        return record

    def get_dataset(self, dataset_id: str) -> DatasetMetadata:
        """Return metadata for a dataset ID."""
        return self.get_record(dataset_id).metadata

    def get_dataframe(self, dataset_id: str) -> pd.DataFrame:
        """Return the stored DataFrame for a dataset ID."""
        return self.get_record(dataset_id).dataframe

    def list_datasets(self) -> list[DatasetMetadata]:
        """Return all datasets, newest first."""
        with self._lock:
            records = list(self._records.values())
        return sorted(
            (record.metadata for record in records),
            key=lambda metadata: metadata.uploaded_at,
            reverse=True,
        )

    def delete_dataset(self, dataset_id: str) -> None:
        """Remove a dataset from memory."""
        with self._lock:
            if self._records.pop(dataset_id, None) is None:
                raise DatasetNotFoundError(dataset_id=dataset_id)
        _logger.info("dataset_removed", dataset_id=dataset_id)

    def count(self) -> int:
        """Return the number of active datasets."""
        with self._lock:
            return len(self._records)

    def clear(self) -> None:
        """Remove all in-memory datasets."""
        with self._lock:
            self._records.clear()
        _logger.info("dataset_manager_cleared")

    async def get_preview(self, dataset_id: str, *, rows: int = 50) -> dict[str, Any]:
        """Return a JSON-serialisable preview for a dataset."""
        try:
            return await asyncio.to_thread(self._get_preview_sync, dataset_id, rows)
        except DataProcessingError:
            raise
        except Exception as exc:
            _logger.exception("preview_generation_failed", dataset_id=dataset_id, error=str(exc))
            raise DataProcessingError(
                message="Failed to generate dataset preview.",
                internal=str(exc),
            ) from exc

    def _register_upload_sync(self, validation: ValidationResult) -> DatasetMetadata:
        dataframe = self._read_dataframe(validation.content, validation.file_type, validation.encoding)
        dataset_id = uuid.uuid4().hex

        metadata = DatasetMetadata(
            dataset_id=dataset_id,
            original_filename=validation.original_filename,
            sanitised_filename=validation.sanitised_filename,
            file_type=validation.file_type,
            content_type=validation.content_type,
            size_bytes=validation.size_bytes,
            encoding=validation.encoding,
            row_count=len(dataframe),
            column_count=len(dataframe.columns),
            columns=list(dataframe.columns),
            has_formula_warnings=validation.has_formula_warnings,
            formula_warning_count=len(validation.formula_warnings),
            uploaded_at=datetime.now(timezone.utc),
        )

        with self._lock:
            self._records[dataset_id] = DatasetRecord(metadata=metadata, dataframe=dataframe)

        _logger.info(
            "dataset_loaded",
            dataset_id=dataset_id,
            filename=validation.sanitised_filename,
            rows=metadata.row_count,
            columns=metadata.column_count,
            size_bytes=validation.size_bytes,
        )

        return metadata

    def _get_preview_sync(self, dataset_id: str, rows: int) -> dict[str, Any]:
        record = self.get_record(dataset_id)
        preview_df = record.dataframe.head(rows)
        preview_df = preview_df.where(preview_df.notna(), None)

        return {
            "columns": list(preview_df.columns),
            "data": preview_df.to_dict(orient="records"),
            "total_rows": record.metadata.row_count,
            "preview_rows": len(preview_df),
        }

    @staticmethod
    def _read_dataframe(
        content: bytes,
        file_type: FileType,
        encoding: str | None,
    ) -> pd.DataFrame:
        """Read a validated upload into a Pandas DataFrame."""
        buffer = io.BytesIO(content)

        try:
            if file_type == FileType.CSV:
                return pd.read_csv(
                    buffer,
                    encoding=encoding or "utf-8",
                    low_memory=False,
                    on_bad_lines="warn",
                )
            if file_type == FileType.XLSX:
                return pd.read_excel(buffer, engine="openpyxl")
            if file_type == FileType.XLS:
                return pd.read_excel(buffer, engine="xlrd")
        except Exception as exc:
            _logger.exception("dataframe_load_failed", file_type=file_type.value, error=str(exc))
            raise DataProcessingError(
                message=f"Failed to load {file_type.value} data into memory.",
                internal=str(exc),
            ) from exc

        raise FileUploadError(message=f"Unsupported file type: {file_type.value}")


_dataframe_manager: DataFrameManager | None = None


def get_dataframe_manager() -> DataFrameManager:
    """Return the module-level DataFrameManager singleton."""
    global _dataframe_manager
    if _dataframe_manager is None:
        _dataframe_manager = DataFrameManager()
    return _dataframe_manager
