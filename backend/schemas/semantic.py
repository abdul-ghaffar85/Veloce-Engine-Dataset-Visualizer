# ═══════════════════════════════════════════════════════════════════════════════
# Veloce Engine — Semantic AI Schemas
# ═══════════════════════════════════════════════════════════════════════════════
"""
Pydantic v2 schemas for the Semantic AI Layer.

These models define business entity classifications mapped to dataset columns.
"""

from __future__ import annotations

import enum

from pydantic import BaseModel, Field


# ═══════════════════════════════════════════════════════════════════════════════
# Enums
# ═══════════════════════════════════════════════════════════════════════════════

class BusinessEntity(str, enum.Enum):
    """
    Business-level semantic classification of a column.
    Provides deeper context beyond primitive data types.
    """
    EMAIL = "email"
    PHONE_NUMBER = "phone_number"
    URL = "url"
    CREDIT_CARD = "credit_card"
    IP_ADDRESS = "ip_address"
    CURRENCY = "currency"
    LATITUDE = "latitude"
    LONGITUDE = "longitude"
    PERSON_NAME = "person_name"
    COMPANY_NAME = "company_name"
    ADDRESS = "address"
    SSN = "ssn"
    COUNTRY = "country"
    CITY = "city"
    STATE = "state"
    ZIP_CODE = "zip_code"
    DATE_TIME = "date_time"
    UNKNOWN = "unknown"


# ═══════════════════════════════════════════════════════════════════════════════
# Models
# ═══════════════════════════════════════════════════════════════════════════════

class ColumnSemanticProfile(BaseModel):
    """Semantic analysis result for a single column."""
    column_name: str = Field(description="Name of the analyzed column.")
    entity_type: BusinessEntity = Field(description="Inferred business entity type.")
    confidence: float = Field(description="Confidence score of the inference (0.0 to 1.0).")
    inference_method: str = Field(description="Method used: 'name_pattern', 'data_regex', or 'fallback'.")


class DatasetSemanticProfile(BaseModel):
    """Complete semantic profile for all columns in a dataset."""
    dataset_id: str
    columns: list[ColumnSemanticProfile] = Field(default_factory=list)


class SemanticAnalysisResponse(BaseModel):
    """API response wrapper for semantic analysis."""
    status: str = "success"
    semantics: DatasetSemanticProfile
