# ═══════════════════════════════════════════════════════════════════════════════
# Veloce Engine — File Validation Service
# ═══════════════════════════════════════════════════════════════════════════════
"""
Centralised file validation for dataset uploads.

Validates:

* **File extension** — only ``.csv``, ``.xlsx``, ``.xls`` are accepted.
* **MIME type** — cross-references the declared content type against an
  allowlist and validates via magic-bytes sniffing.
* **File size** — enforced via streaming byte count (never loads the full
  file into memory).
* **Encoding** — attempts to detect the character encoding for CSV files.
* **Formula injection** — scans CSV content for OWASP CWE-1236 patterns.

This service is stateless and side-effect-free — it receives bytes/metadata
and returns a validated result or raises a domain exception.

Usage::

    from backend.services.file_validator import FileValidationService

    service = FileValidationService()
    result = await service.validate_upload(upload_file)
"""

from __future__ import annotations

import enum
from dataclasses import dataclass, field
from pathlib import PurePath

from fastapi import UploadFile

from backend.core.config import settings
from backend.core.exceptions import (
    FileTooLargeError,
    FileUploadError,
    UnsupportedFileTypeError,
)
from backend.core.logging import get_logger
from backend.utils.security import sanitise_filename, scan_csv_for_formula_injection

_logger = get_logger(__name__)


# ─── Constants ────────────────────────────────────────────────────────────────

class FileType(str, enum.Enum):
    """Supported dataset file types."""
    CSV = "csv"
    XLSX = "xlsx"
    XLS = "xls"


# Extension → allowed MIME types mapping.
_ALLOWED_EXTENSIONS: dict[str, list[str]] = {
    ".csv": [
        "text/csv",
        "text/plain",
        "application/csv",
        "application/vnd.ms-excel",  # Some clients send this for CSV
    ],
    ".xlsx": [
        "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
    ],
    ".xls": [
        "application/vnd.ms-excel",
        "application/x-ole-storage",
    ],
}

# Magic bytes for binary format sniffing.
_MAGIC_BYTES: dict[str, bytes] = {
    ".xlsx": b"PK",                  # ZIP archive (OOXML)
    ".xls": b"\xd0\xcf\x11\xe0",    # OLE2 Compound Document
}

# Streaming chunk size for upload reads (64 KB).
_UPLOAD_CHUNK_SIZE = 64 * 1024


# ─── Validation Result ───────────────────────────────────────────────────────

@dataclass(frozen=True, slots=True)
class ValidationResult:
    """
    Immutable result of file validation.

    Contains all metadata needed by the storage layer to persist the file.
    """
    original_filename: str
    sanitised_filename: str
    file_type: FileType
    extension: str
    content_type: str
    size_bytes: int
    content: bytes
    encoding: str | None = None
    formula_warnings: list[dict[str, int | str]] = field(default_factory=list)

    @property
    def has_formula_warnings(self) -> bool:
        return len(self.formula_warnings) > 0


# ═══════════════════════════════════════════════════════════════════════════════
# Service
# ═══════════════════════════════════════════════════════════════════════════════

class FileValidationService:
    """
    Stateless file validation service.

    All validation methods are instance methods (not classmethods) to
    facilitate future dependency injection of configuration or external
    validation providers.
    """

    def __init__(
        self,
        *,
        max_upload_bytes: int | None = None,
        allowed_extensions: dict[str, list[str]] | None = None,
    ) -> None:
        self._max_bytes = max_upload_bytes or settings.MAX_UPLOAD_SIZE_BYTES
        self._allowed = allowed_extensions or _ALLOWED_EXTENSIONS

    # ─── Public API ──────────────────────────────────────────────────

    async def validate_upload(self, upload: UploadFile) -> ValidationResult:
        """
        Run the full validation pipeline on an uploaded file.

        Pipeline order:

        1. Filename sanitisation + extension check
        2. MIME type validation
        3. Streaming size-limited read
        4. Magic-bytes sniffing (for binary formats)
        5. Encoding detection (for CSV)
        6. Formula injection scan (for CSV)

        Args:
            upload: The FastAPI ``UploadFile`` from the request.

        Returns:
            A ``ValidationResult`` containing validated metadata and content.

        Raises:
            UnsupportedFileTypeError: If the extension or MIME type is disallowed.
            FileTooLargeError: If the file exceeds the size limit.
            FileUploadError: If the file is corrupt or unreadable.
        """
        # 1. Filename & extension
        original_name = upload.filename or "unnamed_file"
        safe_name = sanitise_filename(original_name)
        extension = self._validate_extension(safe_name)
        file_type = self._extension_to_type(extension)

        _logger.info(
            "file_validation_started",
            original=original_name,
            sanitised=safe_name,
            extension=extension,
        )

        # 2. MIME type
        content_type = upload.content_type or "application/octet-stream"
        self._validate_mime_type(content_type, extension, safe_name)

        # 3. Streaming read with size enforcement
        content = await self._read_with_size_limit(upload)
        size_bytes = len(content)

        # 4. Magic bytes (binary formats)
        if extension in _MAGIC_BYTES:
            self._validate_magic_bytes(content, extension, safe_name)

        # 5. Encoding detection (CSV)
        encoding: str | None = None
        if file_type == FileType.CSV:
            encoding = self._detect_encoding(content)

        # 6. Formula injection scan (CSV)
        formula_warnings: list[dict[str, int | str]] = []
        if file_type == FileType.CSV:
            text = content.decode(encoding or "utf-8", errors="replace")
            formula_warnings = scan_csv_for_formula_injection(text)

        _logger.info(
            "file_validation_passed",
            filename=safe_name,
            file_type=file_type.value,
            size_bytes=size_bytes,
            encoding=encoding,
            formula_warnings_count=len(formula_warnings),
        )

        return ValidationResult(
            original_filename=original_name,
            sanitised_filename=safe_name,
            file_type=file_type,
            extension=extension,
            content_type=content_type,
            size_bytes=size_bytes,
            content=content,
            encoding=encoding,
            formula_warnings=formula_warnings,
        )

    # ─── Extension Validation ────────────────────────────────────────

    def _validate_extension(self, filename: str) -> str:
        """
        Extract and validate the file extension.

        Returns:
            The normalised lowercase extension (e.g. ``".csv"``).

        Raises:
            UnsupportedFileTypeError: If the extension is not in the allowlist.
        """
        ext = PurePath(filename).suffix.lower()
        if ext not in self._allowed:
            raise UnsupportedFileTypeError(
                filename=filename,
                allowed_types=list(self._allowed.keys()),
            )
        return ext

    def _extension_to_type(self, extension: str) -> FileType:
        """Map a validated extension string to a ``FileType`` enum."""
        mapping = {
            ".csv": FileType.CSV,
            ".xlsx": FileType.XLSX,
            ".xls": FileType.XLS,
        }
        return mapping[extension]

    # ─── MIME Type Validation ────────────────────────────────────────

    def _validate_mime_type(
        self,
        content_type: str,
        extension: str,
        filename: str,
    ) -> None:
        """
        Cross-reference the declared MIME type against the extension allowlist.

        ``application/octet-stream`` is always accepted as a fallback because
        many clients fail to detect the correct MIME type.

        Raises:
            UnsupportedFileTypeError: If the MIME type is incompatible.
        """
        allowed_mimes = self._allowed.get(extension, [])
        # Always allow generic binary stream — many clients use this as default.
        if content_type == "application/octet-stream":
            return
        if content_type not in allowed_mimes:
            _logger.warning(
                "mime_type_mismatch",
                filename=filename,
                extension=extension,
                declared_mime=content_type,
                allowed_mimes=allowed_mimes,
            )
            raise UnsupportedFileTypeError(
                filename=filename,
                allowed_types=list(self._allowed.keys()),
            )

    # ─── Size-Limited Streaming Read ─────────────────────────────────

    async def _read_with_size_limit(self, upload: UploadFile) -> bytes:
        """
        Read the upload file in chunks, enforcing the size limit.

        This prevents memory exhaustion from maliciously large files — the
        connection is aborted as soon as the limit is crossed, without
        buffering the entire payload.

        Raises:
            FileTooLargeError: If accumulated bytes exceed the limit.
            FileUploadError: If the file cannot be read.
        """
        chunks: list[bytes] = []
        total = 0

        try:
            while True:
                chunk = await upload.read(_UPLOAD_CHUNK_SIZE)
                if not chunk:
                    break
                total += len(chunk)
                if total > self._max_bytes:
                    raise FileTooLargeError(max_bytes=self._max_bytes)
                chunks.append(chunk)
        except FileTooLargeError:
            raise
        except Exception as exc:
            _logger.error(
                "file_read_error",
                error=str(exc),
                filename=upload.filename,
            )
            raise FileUploadError(
                message="Failed to read the uploaded file.",
                internal=str(exc),
            ) from exc

        if total == 0:
            raise FileUploadError(message="Uploaded file is empty.")

        return b"".join(chunks)

    # ─── Magic Bytes Sniffing ────────────────────────────────────────

    def _validate_magic_bytes(
        self,
        content: bytes,
        extension: str,
        filename: str,
    ) -> None:
        """
        Verify that the file's magic bytes match the expected extension.

        Raises:
            FileUploadError: If the magic bytes do not match.
        """
        expected = _MAGIC_BYTES.get(extension)
        if expected and not content[:len(expected)].startswith(expected):
            _logger.warning(
                "magic_bytes_mismatch",
                filename=filename,
                extension=extension,
                expected_prefix=expected.hex(),
                actual_prefix=content[:8].hex(),
            )
            raise FileUploadError(
                message=(
                    f"File content does not match the expected format for "
                    f"'{extension}' files. The file may be corrupt or mislabeled."
                ),
            )

    # ─── Encoding Detection ──────────────────────────────────────────

    @staticmethod
    def _detect_encoding(content: bytes) -> str:
        """
        Detect the character encoding of a byte stream.

        Uses a simple BOM-based heuristic with UTF-8 as the default.
        For production use with diverse encodings, ``chardet`` or
        ``charset_normalizer`` could be added as an optional dependency.

        Returns:
            The detected encoding string (e.g. ``"utf-8"``, ``"utf-16"``).
        """
        # Check for BOM markers
        if content[:3] == b"\xef\xbb\xbf":
            return "utf-8-sig"
        if content[:2] in (b"\xff\xfe", b"\xfe\xff"):
            return "utf-16"

        # Try UTF-8 decode
        try:
            content[:8192].decode("utf-8")
            return "utf-8"
        except UnicodeDecodeError:
            pass

        # Fallback to latin-1 (always succeeds — every byte is valid)
        return "latin-1"
