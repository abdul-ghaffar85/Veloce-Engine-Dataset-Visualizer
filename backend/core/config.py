# ═══════════════════════════════════════════════════════════════════════════════
# Veloce Engine — Application Configuration
# ═══════════════════════════════════════════════════════════════════════════════
"""
Centralised, type-safe application configuration.

All settings are loaded from environment variables (with ``.env`` fallback)
using Pydantic Settings v2.  Validation runs at import time so the process
fails fast on misconfiguration rather than at first use.

Usage::

    from backend.core.config import settings

    print(settings.APP_NAME)          # "Veloce Engine"
    print(settings.cors_origin_list)  # ["http://localhost:5173", ...]
"""

from __future__ import annotations

import enum
from functools import lru_cache
from pathlib import Path
from pydantic import (
    Field,
    field_validator,
)
from pydantic_settings import BaseSettings, SettingsConfigDict

# ─── Constants ────────────────────────────────────────────────────────────────

_PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent
"""Absolute path to the repository root (two levels above backend/core/)."""

_100_MB = 104_857_600


# ─── Enums ────────────────────────────────────────────────────────────────────

class AppEnvironment(str, enum.Enum):
    """Valid deployment stages."""

    DEVELOPMENT = "development"
    STAGING = "staging"
    PRODUCTION = "production"
    TESTING = "testing"


class LogFormat(str, enum.Enum):
    """Supported log output formats."""

    JSON = "json"
    CONSOLE = "console"


# ─── Settings ─────────────────────────────────────────────────────────────────

class Settings(BaseSettings):
    """
    Immutable, validated application settings.

    Every field maps 1-to-1 to an environment variable.  Defaults are tuned
    for *development*; production overrides should be provided via ``.env``
    or a secrets manager.
    """

    model_config = SettingsConfigDict(
        env_file=str(_PROJECT_ROOT / ".env"),
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )

    # ── Application ──────────────────────────────────────────────────────
    APP_NAME: str = "Veloce Engine"
    APP_VERSION: str = "0.1.0"
    APP_ENV: AppEnvironment = AppEnvironment.DEVELOPMENT
    APP_DEBUG: bool = True

    # ── Server ───────────────────────────────────────────────────────────
    APP_HOST: str = "0.0.0.0"
    APP_PORT: int = Field(default=8000, ge=1, le=65535)
    APP_WORKERS: int = Field(default=1, ge=1, le=32)

    # ── CORS ─────────────────────────────────────────────────────────────
    CORS_ORIGINS: str = "http://localhost:5173,http://localhost:3000"

    # ── File Upload ──────────────────────────────────────────────────────
    MAX_UPLOAD_SIZE_BYTES: int = Field(default=_100_MB, ge=1)
    UPLOAD_DIR: Path = Field(default=Path("data/uploads"))

    # ── Logging ──────────────────────────────────────────────────────────
    LOG_LEVEL: str = "DEBUG"
    LOG_FORMAT: LogFormat = LogFormat.JSON
    LOG_FILE: Path | None = Field(default=Path("logs/veloce.log"))

    # ── Rate Limiting ────────────────────────────────────────────────────
    RATE_LIMIT_PER_MINUTE: int = Field(default=120, ge=1)

    # ── Derived Properties ───────────────────────────────────────────────

    @property
    def cors_origin_list(self) -> list[str]:
        """Parse the comma-separated CORS origins into a list."""
        return [
            origin.strip()
            for origin in self.CORS_ORIGINS.split(",")
            if origin.strip()
        ]

    @property
    def is_development(self) -> bool:
        return self.APP_ENV == AppEnvironment.DEVELOPMENT

    @property
    def project_root(self) -> Path:
        return _PROJECT_ROOT

    @property
    def resolved_upload_dir(self) -> Path:
        """Absolute upload directory, resolved relative to project root."""
        if self.UPLOAD_DIR.is_absolute():
            return self.UPLOAD_DIR
        return _PROJECT_ROOT / self.UPLOAD_DIR

    @property
    def resolved_log_file(self) -> Path | None:
        """Absolute log file path, resolved relative to project root."""
        if self.LOG_FILE is None:
            return None
        if self.LOG_FILE.is_absolute():
            return self.LOG_FILE
        return _PROJECT_ROOT / self.LOG_FILE

    # ── Validators ───────────────────────────────────────────────────────

    @field_validator("LOG_LEVEL")
    @classmethod
    def _normalise_log_level(cls, value: str) -> str:
        normalised = value.upper().strip()
        valid_levels = {"DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"}
        if normalised not in valid_levels:
            raise ValueError(
                f"LOG_LEVEL must be one of {valid_levels}, got '{value}'"
            )
        return normalised


# ─── Singleton Access ─────────────────────────────────────────────────────────

@lru_cache(maxsize=1)
def get_settings() -> Settings:
    """
    Return the singleton application settings instance.

    The first call validates and caches; subsequent calls return the cached
    instance with zero overhead.
    """
    return Settings()


settings: Settings = get_settings()
"""Module-level convenience reference to the validated settings."""
