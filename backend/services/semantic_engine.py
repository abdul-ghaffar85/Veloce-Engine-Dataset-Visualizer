# ═══════════════════════════════════════════════════════════════════════════════
# Veloce Engine — Semantic AI Engine
# ═══════════════════════════════════════════════════════════════════════════════
"""
Automatic Semantic AI Layer for Business Entity Recognition.

Analyzes dataset columns to infer their higher-level business meaning 
(e.g., Email, Phone Number, Currency, Address) using a combination of:
1. Column name heuristics (fastest, high confidence for standard names)
2. Value-based Regex sampling (robust, handles obfuscated column names)

All heavy computation is offloaded to a thread pool.

Usage::

    from backend.services.semantic_engine import get_semantic_engine

    engine = get_semantic_engine()
    semantics = await engine.analyze_dataset(dataset_id, df)
"""

from __future__ import annotations

import asyncio
import re
from typing import Any

import pandas as pd

from backend.core.exceptions import DataProcessingError
from backend.core.logging import get_logger
from backend.schemas.semantic import (
    BusinessEntity,
    ColumnSemanticProfile,
    DatasetSemanticProfile,
)

_logger = get_logger(__name__)


# ─── Heuristic Patterns ──────────────────────────────────────────────────────

# Column name patterns (case-insensitive) mapped to entities
_NAME_PATTERNS: dict[BusinessEntity, list[str]] = {
    BusinessEntity.EMAIL: ["email", "e-mail", "mail_address"],
    BusinessEntity.PHONE_NUMBER: ["phone", "mobile", "cell", "telephone", "fax"],
    BusinessEntity.URL: ["url", "website", "link", "domain"],
    BusinessEntity.IP_ADDRESS: ["ip_address", "ipv4", "ipv6", "ip"],
    BusinessEntity.PERSON_NAME: ["name", "first_name", "last_name", "full_name", "surname"],
    BusinessEntity.COMPANY_NAME: ["company", "organization", "employer", "business", "client_name"],
    BusinessEntity.ADDRESS: ["address", "street", "line_1", "line_2"],
    BusinessEntity.CITY: ["city", "municipality", "town"],
    BusinessEntity.STATE: ["state", "province", "region"],
    BusinessEntity.COUNTRY: ["country", "nation"],
    BusinessEntity.ZIP_CODE: ["zip", "postal_code", "postcode"],
    BusinessEntity.LATITUDE: ["latitude", "lat"],
    BusinessEntity.LONGITUDE: ["longitude", "lon", "lng"],
    BusinessEntity.SSN: ["ssn", "social_security"],
    BusinessEntity.CREDIT_CARD: ["card_number", "credit_card", "cc_num"],
    BusinessEntity.CURRENCY: ["amount", "price", "cost", "salary", "revenue", "budget", "total", "fee", "tax"],
}

# Regex patterns for data value sampling
_DATA_REGEX_PATTERNS: dict[BusinessEntity, re.Pattern] = {
    BusinessEntity.EMAIL: re.compile(r"^[a-zA-Z0-9_.+-]+@[a-zA-Z0-9-]+\.[a-zA-Z0-9-.]+$"),
    BusinessEntity.URL: re.compile(r"^(https?:\/\/)?([\da-z\.-]+)\.([a-z\.]{2,6})([\/\w \.-]*)*\/?$"),
    BusinessEntity.IP_ADDRESS: re.compile(r"^(?:[0-9]{1,3}\.){3}[0-9]{1,3}$"),
    BusinessEntity.SSN: re.compile(r"^(?!000|666)[0-8][0-9]{2}-(?!00)[0-9]{2}-(?!0000)[0-9]{4}$"),
    BusinessEntity.CREDIT_CARD: re.compile(r"^(?:4[0-9]{12}(?:[0-9]{3})?|5[1-5][0-9]{14}|3[47][0-9]{13}|3(?:0[0-5]|[68][0-9])[0-9]{11}|6(?:011|5[0-9]{2})[0-9]{12}|(?:2131|1800|35\d{3})\d{11})$"),
    BusinessEntity.ZIP_CODE: re.compile(r"^\d{5}(?:[-\s]\d{4})?$"),
}

_MAX_SAMPLE_SIZE = 100
_MIN_MATCH_THRESHOLD = 0.8  # 80% of sampled non-null rows must match the regex


# ═══════════════════════════════════════════════════════════════════════════════
# Semantic Engine Service
# ═══════════════════════════════════════════════════════════════════════════════

class SemanticEngineService:
    """
    Stateless Semantic AI Layer for Business Entity Recognition.
    Executes Pandas/Regex operations in a thread pool.
    """

    async def analyze_dataset(
        self,
        dataset_id: str,
        df: pd.DataFrame,
    ) -> DatasetSemanticProfile:
        """
        Analyze a full dataset to infer business entities for each column.
        """
        try:
            return await asyncio.to_thread(self._analyze_sync, dataset_id, df)
        except Exception as exc:
            _logger.exception("semantic_analysis_failed", dataset_id=dataset_id, error=str(exc))
            raise DataProcessingError(
                message="Failed to perform semantic analysis on dataset.",
                internal=str(exc),
            ) from exc

    # ─── Synchronous Implementations ─────────────────────────────────

    def _analyze_sync(
        self,
        dataset_id: str,
        df: pd.DataFrame,
    ) -> DatasetSemanticProfile:
        _logger.info("semantic_analysis_started", dataset_id=dataset_id, columns=len(df.columns))

        columns = []
        for col_name in df.columns:
            profile = self._analyze_column(col_name, df[col_name])
            columns.append(profile)

        return DatasetSemanticProfile(
            dataset_id=dataset_id,
            columns=columns,
        )

    def _analyze_column(
        self,
        col_name: str,
        series: pd.Series,
    ) -> ColumnSemanticProfile:
        """
        Infers the business entity of a single column.
        Uses Name Heuristics first. If not confident, falls back to Data Regex Heuristics.
        """
        col_lower = col_name.lower().strip()

        # 1. Name Pattern Heuristics (Fastest, High Confidence)
        for entity, patterns in _NAME_PATTERNS.items():
            for pattern in patterns:
                # Exact match or standard suffix/prefix
                if col_lower == pattern or col_lower.endswith(f"_{pattern}") or col_lower.startswith(f"{pattern}_"):
                    return ColumnSemanticProfile(
                        column_name=col_name,
                        entity_type=entity,
                        confidence=0.95,
                        inference_method="name_pattern",
                    )
                # Partial match (lower confidence)
                elif pattern in col_lower:
                    # Don't return immediately, allow data regex to potentially override or confirm
                    # But if no data regex matches later, we'll use this
                    pass

        # 2. Data Regex Heuristics (Robust, Value-based)
        non_null = series.dropna()
        if len(non_null) > 0:
            # Sample data for performance
            sample = non_null.sample(min(len(non_null), _MAX_SAMPLE_SIZE)).astype(str)
            
            for entity, regex in _DATA_REGEX_PATTERNS.items():
                # Count how many sampled values match the regex
                matches = sample.str.match(regex).sum()
                match_ratio = matches / len(sample)

                if match_ratio >= _MIN_MATCH_THRESHOLD:
                    return ColumnSemanticProfile(
                        column_name=col_name,
                        entity_type=entity,
                        confidence=round(match_ratio, 4),
                        inference_method="data_regex",
                    )

        # 3. Partial Name Matching Fallback
        for entity, patterns in _NAME_PATTERNS.items():
            for pattern in patterns:
                if pattern in col_lower:
                    return ColumnSemanticProfile(
                        column_name=col_name,
                        entity_type=entity,
                        confidence=0.60, # Lower confidence for partial name match
                        inference_method="name_pattern_partial",
                    )

        # 4. Fallback for Datetime (If Pandas parsed it as datetime previously)
        if pd.api.types.is_datetime64_any_dtype(series):
             return ColumnSemanticProfile(
                column_name=col_name,
                entity_type=BusinessEntity.DATE_TIME,
                confidence=1.0,
                inference_method="pandas_dtype",
            )

        # 5. Default Fallback
        return ColumnSemanticProfile(
            column_name=col_name,
            entity_type=BusinessEntity.UNKNOWN,
            confidence=0.0,
            inference_method="fallback",
        )


# ─── Module-level Singleton ──────────────────────────────────────────────────

_semantic_engine: SemanticEngineService | None = None

def get_semantic_engine() -> SemanticEngineService:
    global _semantic_engine
    if _semantic_engine is None:
        _semantic_engine = SemanticEngineService()
    return _semantic_engine
