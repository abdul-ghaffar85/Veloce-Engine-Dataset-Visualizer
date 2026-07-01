# ═══════════════════════════════════════════════════════════════════════════════
# Veloce Engine — Report Builder Service
# ═══════════════════════════════════════════════════════════════════════════════
"""
Automatic Report Generation Engine.

Exports datasets to standard business formats (CSV, Excel). Supports dynamic
query application before export, allowing users to download exactly what they
see on their filtered/grouped dashboard grids.

Usage::

    from backend.services.report_engine import get_report_engine

    engine = get_report_engine()
    file_bytes, filename, media_type = await engine.generate_export(dataset_id, df, request)
"""

from __future__ import annotations

import asyncio
import io

import pandas as pd

from backend.core.exceptions import DataProcessingError
from backend.core.logging import get_logger
from backend.schemas.report import ExportFormat, ExportRequest
from backend.services.aggregation_engine import get_aggregation_engine

_logger = get_logger(__name__)


# ═══════════════════════════════════════════════════════════════════════════════
# Report Engine Service
# ═══════════════════════════════════════════════════════════════════════════════

class ReportEngineService:
    """
    Stateless engine to generate exportable files from DataFrames.
    """

    async def generate_export(
        self,
        dataset_id: str,
        df: pd.DataFrame,
        request: ExportRequest,
    ) -> tuple[bytes, str, str]:
        """
        Generate an export file asynchronously.
        Returns a tuple of (file_bytes, filename, media_type).
        """
        try:
            return await asyncio.to_thread(self._generate_sync, dataset_id, df, request)
        except Exception as exc:
            _logger.exception("report_generation_failed", dataset_id=dataset_id, error=str(exc))
            raise DataProcessingError("Failed to generate export file.", str(exc)) from exc

    # ─── Synchronous Implementation ────────────────────────────────

    def _generate_sync(
        self, dataset_id: str, df: pd.DataFrame, request: ExportRequest
    ) -> tuple[bytes, str, str]:
        _logger.info("generating_report", dataset_id=dataset_id, format=request.format.value)

        # 1. Apply Dynamic Query (if provided)
        if request.query:
            agg_engine = get_aggregation_engine()
            
            # Apply standard aggregation pipeline, bypassing pagination 
            # to export the full matched dataset.
            df = agg_engine._apply_filters(df, request.query)
            df = agg_engine._apply_aggregations(df, request.query)
            df = agg_engine._apply_sort(df, request.query)

        if df.empty:
            _logger.warning("export_empty_dataset", dataset_id=dataset_id)

        # 2. Serialize to requested format
        if request.format == ExportFormat.CSV:
            file_bytes = df.to_csv(index=False).encode("utf-8")
            ext = "csv"
            media_type = "text/csv"
        elif request.format == ExportFormat.EXCEL:
            buffer = io.BytesIO()
            with pd.ExcelWriter(buffer, engine="openpyxl") as writer:
                # Truncate sheet name to 31 chars (Excel limit)
                sheet_name = str(dataset_id)[:31]
                df.to_excel(writer, index=False, sheet_name=sheet_name)
            file_bytes = buffer.getvalue()
            ext = "xlsx"
            media_type = "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
        else:
            raise ValueError(f"Unsupported export format: {request.format}")

        # 3. Determine Filename
        filename = request.file_name or f"export_{dataset_id}.{ext}"
        if not filename.lower().endswith(f".{ext}"):
            filename += f".{ext}"

        return file_bytes, filename, media_type


# ─── Module-level Singleton ──────────────────────────────────────────────────

_report_engine: ReportEngineService | None = None

def get_report_engine() -> ReportEngineService:
    global _report_engine
    if _report_engine is None:
        _report_engine = ReportEngineService()
    return _report_engine
