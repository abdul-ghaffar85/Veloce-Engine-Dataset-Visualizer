# ═══════════════════════════════════════════════════════════════════════════════
# Veloce Engine — Dataset API Routes
# ═══════════════════════════════════════════════════════════════════════════════
"""
API v1 endpoints for dataset upload, management, preview, and profiling.

Endpoints:

* ``POST   /api/v1/datasets/upload``              — Upload a single file.
* ``POST   /api/v1/datasets/upload/batch``         — Upload multiple files.
* ``GET    /api/v1/datasets``                      — List all datasets.
* ``GET    /api/v1/datasets/{dataset_id}``         — Get dataset metadata.
* ``DELETE /api/v1/datasets/{dataset_id}``         — Delete a dataset.
* ``GET    /api/v1/datasets/{dataset_id}/preview`` — Preview first N rows.
* ``GET    /api/v1/datasets/{dataset_id}/profile`` — Full dataset profile.
"""

from __future__ import annotations

from fastapi import APIRouter, File, Query, UploadFile
from fastapi.responses import ORJSONResponse

from backend.core.logging import get_logger
from backend.schemas.dataset import (
    BatchUploadResponse,
    BatchUploadResult,
    DatasetListResponse,
    DatasetResponse,
    DeleteResponse,
    PreviewResponse,
    UploadResponse,
)
from backend.schemas.profile import ProfileResponse
from backend.services.file_validator import FileValidationService
from backend.services.profiler import get_profiling_service
from backend.services.dataframe_manager import DatasetMetadata, get_dataframe_manager

_logger = get_logger(__name__)

router = APIRouter(
    prefix="/api/v1/datasets",
    tags=["Datasets"],
    default_response_class=ORJSONResponse,
)

# ─── Service Instances ───────────────────────────────────────────────────────
# These could be injected via FastAPI Depends() for more granular testing.
# For now, module-level singletons keep the code simple and fast.

_validator = FileValidationService()


# ═══════════════════════════════════════════════════════════════════════════════
# Helpers
# ═══════════════════════════════════════════════════════════════════════════════

def _metadata_to_response(meta: DatasetMetadata) -> DatasetResponse:
    """Map an internal ``DatasetMetadata`` to the API ``DatasetResponse``."""
    return DatasetResponse(
        dataset_id=meta.dataset_id,
        original_filename=meta.original_filename,
        file_type=meta.file_type.value,
        size_bytes=meta.size_bytes,
        size_display=DatasetResponse.format_size(meta.size_bytes),
        encoding=meta.encoding,
        row_count=meta.row_count,
        column_count=meta.column_count,
        columns=meta.columns,
        has_formula_warnings=meta.has_formula_warnings,
        formula_warning_count=meta.formula_warning_count,
        uploaded_at=meta.uploaded_at,
    )


# ═══════════════════════════════════════════════════════════════════════════════
# Upload — Single File
# ═══════════════════════════════════════════════════════════════════════════════

@router.post(
    "/upload",
    response_model=UploadResponse,
    status_code=201,
    summary="Upload a single dataset",
    description=(
        "Upload a CSV or Excel file. The file is validated for type, size, "
        "encoding, and formula injection before being loaded into memory."
    ),
)
async def upload_dataset(
    file: UploadFile = File(
        ...,
        description="A CSV (.csv), Excel (.xlsx), or legacy Excel (.xls) file.",
    ),
) -> UploadResponse:
    """
    Upload and validate a single dataset file.

    The upload pipeline:

    1. Validate extension, MIME type, size, encoding, and formula injection.
    2. Load the DataFrame into the in-memory manager.
    3. Derive schema info (row count, columns).
    4. Return metadata response.
    """
    manager = get_dataframe_manager()

    _logger.info(
        "upload_request_received",
        filename=file.filename,
        content_type=file.content_type,
    )

    # Validate
    validation = await _validator.validate_upload(file)

    # Store
    metadata = await manager.register_upload(validation)

    _logger.info(
        "upload_completed",
        dataset_id=metadata.dataset_id,
        filename=metadata.original_filename,
        rows=metadata.row_count,
        columns=metadata.column_count,
    )

    return UploadResponse(
        dataset=_metadata_to_response(metadata),
    )


# ═══════════════════════════════════════════════════════════════════════════════
# Upload — Batch (Multiple Files)
# ═══════════════════════════════════════════════════════════════════════════════

@router.post(
    "/upload/batch",
    response_model=BatchUploadResponse,
    status_code=201,
    summary="Upload multiple datasets",
    description=(
        "Upload multiple CSV or Excel files in a single request. "
        "Each file is validated and loaded independently; partial failures "
        "do not affect other files."
    ),
)
async def upload_batch(
    files: list[UploadFile] = File(
        ...,
        description="One or more CSV/Excel files.",
    ),
) -> BatchUploadResponse:
    """
    Upload multiple files with individual error isolation.

    Each file is processed independently — if one fails validation,
    the others are still loaded.
    """
    manager = get_dataframe_manager()
    results: list[BatchUploadResult] = []
    succeeded = 0
    failed = 0

    _logger.info("batch_upload_started", file_count=len(files))

    for upload_file in files:
        filename = upload_file.filename or "unnamed_file"
        try:
            validation = await _validator.validate_upload(upload_file)
            metadata = await manager.register_upload(validation)
            results.append(
                BatchUploadResult(
                    filename=filename,
                    status="success",
                    dataset=_metadata_to_response(metadata),
                )
            )
            succeeded += 1
        except Exception as exc:
            _logger.warning(
                "batch_file_failed",
                filename=filename,
                error=str(exc),
            )
            results.append(
                BatchUploadResult(
                    filename=filename,
                    status="error",
                    error=str(exc),
                )
            )
            failed += 1

    _logger.info(
        "batch_upload_completed",
        total=len(files),
        succeeded=succeeded,
        failed=failed,
    )

    return BatchUploadResponse(
        total=len(files),
        succeeded=succeeded,
        failed=failed,
        results=results,
    )


# ═══════════════════════════════════════════════════════════════════════════════
# List Datasets
# ═══════════════════════════════════════════════════════════════════════════════

@router.get(
    "",
    response_model=DatasetListResponse,
    summary="List all datasets",
    description="Retrieve metadata for all uploaded datasets, newest first.",
)
async def list_datasets() -> DatasetListResponse:
    """Return all dataset metadata records."""
    manager = get_dataframe_manager()
    datasets = manager.list_datasets()

    return DatasetListResponse(
        count=len(datasets),
        datasets=[_metadata_to_response(m) for m in datasets],
    )


# ═══════════════════════════════════════════════════════════════════════════════
# Get Dataset by ID
# ═══════════════════════════════════════════════════════════════════════════════

@router.get(
    "/{dataset_id}",
    response_model=UploadResponse,
    summary="Get dataset metadata",
    description="Retrieve metadata for a specific dataset by its ID.",
)
async def get_dataset(dataset_id: str) -> UploadResponse:
    """
    Return metadata for a single dataset.

    Raises:
        404: If the dataset ID does not exist.
    """
    manager = get_dataframe_manager()
    metadata = manager.get_dataset(dataset_id)

    return UploadResponse(
        message="Dataset retrieved successfully.",
        dataset=_metadata_to_response(metadata),
    )


# ═══════════════════════════════════════════════════════════════════════════════
# Delete Dataset
# ═══════════════════════════════════════════════════════════════════════════════

@router.delete(
    "/{dataset_id}",
    response_model=DeleteResponse,
    summary="Delete a dataset",
    description="Delete a dataset's file and metadata by its ID.",
)
async def delete_dataset(dataset_id: str) -> DeleteResponse:
    """
    Delete a dataset and its stored file.

    Raises:
        404: If the dataset ID does not exist.
    """
    manager = get_dataframe_manager()
    manager.delete_dataset(dataset_id)

    _logger.info("dataset_deleted_via_api", dataset_id=dataset_id)

    return DeleteResponse(dataset_id=dataset_id)


# ═══════════════════════════════════════════════════════════════════════════════
# Preview Dataset
# ═══════════════════════════════════════════════════════════════════════════════

@router.get(
    "/{dataset_id}/preview",
    response_model=PreviewResponse,
    summary="Preview dataset rows",
    description=(
        "Return the first N rows of a dataset for quick inspection. "
        "Default is 50 rows; max is 500."
    ),
)
async def preview_dataset(
    dataset_id: str,
    rows: int = Query(
        default=50,
        ge=1,
        le=500,
        description="Number of rows to preview (1–500).",
    ),
) -> PreviewResponse:
    """
    Return a row preview for the dataset.

    Raises:
        404: If the dataset ID does not exist.
        500: If the file cannot be read.
    """
    manager = get_dataframe_manager()
    preview = await manager.get_preview(dataset_id, rows=rows)

    return PreviewResponse(
        dataset_id=dataset_id,
        columns=preview["columns"],
        data=preview["data"],
        total_rows=preview["total_rows"],
        preview_rows=preview["preview_rows"],
    )


# ═══════════════════════════════════════════════════════════════════════════════
# Profile Dataset
# ═══════════════════════════════════════════════════════════════════════════════

@router.get(
    "/{dataset_id}/profile",
    response_model=ProfileResponse,
    summary="Profile a dataset",
    description=(
        "Run the full profiling engine on a dataset. Returns per-column "
        "statistics, semantic type inference, outlier detection, missing "
        "value analysis, and automatic dimension/measure classification."
    ),
)
async def profile_dataset(dataset_id: str) -> ProfileResponse:
    """
    Generate a comprehensive profile for the dataset.

    The profiling pipeline:

    1. Load the dataset file via Pandas (in a thread pool).
    2. Run semantic type inference on every column.
    3. Compute descriptive statistics, cardinality, outliers.
    4. Classify columns as dimension / measure / time / identifier.
    5. Return the full ``DatasetProfile``.

    Raises:
        404: If the dataset ID does not exist.
        500: If profiling fails.
    """
    manager = get_dataframe_manager()
    profiler = get_profiling_service()

    metadata = manager.get_dataset(dataset_id)
    df = manager.get_dataframe(dataset_id)

    _logger.info(
        "profile_request",
        dataset_id=dataset_id,
        rows=len(df),
        columns=len(df.columns),
    )

    profile = await profiler.profile_dataset(
        dataset_id=dataset_id,
        filename=metadata.original_filename,
        df=df,
    )

    return ProfileResponse(profile=profile)
