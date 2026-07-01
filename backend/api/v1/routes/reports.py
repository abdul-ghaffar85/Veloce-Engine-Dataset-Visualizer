# ═══════════════════════════════════════════════════════════════════════════════
# Veloce Engine — Report API Routes
# ═══════════════════════════════════════════════════════════════════════════════
"""
API v1 endpoints for the Report Builder.

Endpoints:

* ``POST /api/v1/reports/export/{dataset_id}`` — Export a raw or filtered dataset to CSV/Excel.
"""

from __future__ import annotations

from fastapi import APIRouter
from fastapi.responses import Response

from backend.core.logging import get_logger
from backend.schemas.report import ExportRequest
from backend.services.report_engine import get_report_engine
from backend.services.dataframe_manager import get_dataframe_manager

_logger = get_logger(__name__)

router = APIRouter(
    prefix="/api/v1/reports",
    tags=["Reports"],
    # Note: We do not use ORJSONResponse here because this endpoint returns raw bytes
)


# ═══════════════════════════════════════════════════════════════════════════════
# Export Dataset
# ═══════════════════════════════════════════════════════════════════════════════

@router.post(
    "/export/{dataset_id}",
    summary="Export dataset to CSV or Excel",
    description=(
        "Generates a downloadable file (CSV or XLSX). Accepts an optional "
        "Aggregation Engine query payload to filter, group, or sort the data "
        "exactly as it appears on the dashboard before exporting."
    ),
    response_class=Response,
    responses={
        200: {
            "description": "A downloadable file.",
            "content": {
                "text/csv": {},
                "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet": {}
            }
        }
    }
)
async def export_dataset(dataset_id: str, request: ExportRequest) -> Response:
    """
    Generate and return a file export.
    """
    manager = get_dataframe_manager()
    engine = get_report_engine()

    df = manager.get_dataframe(dataset_id)

    file_bytes, filename, media_type = await engine.generate_export(dataset_id, df, request)

    # Return raw response with file attachment headers
    return Response(
        content=file_bytes,
        media_type=media_type,
        headers={
            "Content-Disposition": f'attachment; filename="{filename}"'
        }
    )
