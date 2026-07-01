# ═══════════════════════════════════════════════════════════════════════════════
# Veloce Engine — Security Utilities
# ═══════════════════════════════════════════════════════════════════════════════
"""
Security-focused utilities for file upload processing.

Responsibilities:

* **Filename sanitisation** — strips path components, null bytes, control
  characters, and shell metacharacters.  Collapses leading dots to prevent
  hidden-file creation on Unix.
* **Path traversal prevention** — ensures the resolved storage path stays
  within the designated upload directory.
* **Formula injection detection** — flags CSV cells that begin with ``=``,
  ``+``, ``-``, ``@``, ``\\t``, or ``\\r`` which could trigger execution
  in spreadsheet applications (CWE-1236).

Usage::

    from backend.utils.security import sanitise_filename, check_path_traversal

    safe = sanitise_filename("../../etc/passwd")       # "etc_passwd"
    check_path_traversal(Path("uploads/abc.csv"), Path("uploads"))  # OK
"""

from __future__ import annotations

import re
import unicodedata
from pathlib import Path, PurePosixPath, PureWindowsPath

from backend.core.logging import get_logger

_logger = get_logger(__name__)

# ─── Constants ────────────────────────────────────────────────────────────────

# Characters that are unsafe in filenames across Windows, Linux, and macOS.
_UNSAFE_CHARS_RE = re.compile(r'[<>:"/\\|?*\x00-\x1f]')

# Prefixes that trigger formula execution in Excel / Google Sheets / LibreOffice.
# See: https://owasp.org/www-community/attacks/CSV_Injection
_FORMULA_PREFIXES: tuple[str, ...] = ("=", "+", "-", "@", "\t", "\r")

# Maximum filename length (most filesystems cap at 255 bytes).
_MAX_FILENAME_LENGTH = 200


# ═══════════════════════════════════════════════════════════════════════════════
# Filename Sanitisation
# ═══════════════════════════════════════════════════════════════════════════════

def sanitise_filename(filename: str) -> str:
    """
    Produce a filesystem-safe version of a user-supplied filename.

    Steps:

    1. Normalise Unicode to NFC form.
    2. Extract the basename (strip any directory path components).
    3. Remove null bytes and control characters.
    4. Replace OS-unsafe characters with underscores.
    5. Collapse consecutive underscores / dots.
    6. Strip leading dots (prevents hidden files / directory escape).
    7. Truncate to ``_MAX_FILENAME_LENGTH`` while preserving the extension.
    8. Fall back to ``"unnamed_file"`` if the result is empty.

    Args:
        filename: The raw filename from the upload request.

    Returns:
        A sanitised, filesystem-safe filename string.
    """
    if not filename or not filename.strip():
        return "unnamed_file"

    # 1. Unicode normalisation
    name = unicodedata.normalize("NFC", filename.strip())

    # 2. Strip directory components (handles both / and \ separators)
    name = PurePosixPath(PureWindowsPath(name).name).name

    # 3. Remove null bytes
    name = name.replace("\x00", "")

    # 4. Replace unsafe characters
    name = _UNSAFE_CHARS_RE.sub("_", name)

    # 5. Collapse runs of underscores and dots
    name = re.sub(r"_{2,}", "_", name)
    name = re.sub(r"\.{2,}", ".", name)

    # 6. Strip leading dots and underscores
    name = name.lstrip("._")

    # 7. Truncate while keeping extension
    if len(name) > _MAX_FILENAME_LENGTH:
        stem_path = Path(name)
        suffix = stem_path.suffix  # e.g. ".csv"
        max_stem = _MAX_FILENAME_LENGTH - len(suffix)
        name = stem_path.stem[:max_stem] + suffix

    # 8. Fallback
    if not name or name == ".":
        return "unnamed_file"

    return name


# ═══════════════════════════════════════════════════════════════════════════════
# Path Traversal Prevention
# ═══════════════════════════════════════════════════════════════════════════════

def check_path_traversal(file_path: Path, base_dir: Path) -> None:
    """
    Verify that ``file_path`` resolves within ``base_dir``.

    Raises:
        ValueError: If the resolved path escapes the base directory.
    """
    resolved = file_path.resolve()
    base_resolved = base_dir.resolve()

    if not str(resolved).startswith(str(base_resolved)):
        _logger.warning(
            "path_traversal_attempt",
            file_path=str(file_path),
            base_dir=str(base_dir),
            resolved=str(resolved),
        )
        raise ValueError(
            "Path traversal detected: file path escapes the upload directory."
        )


# ═══════════════════════════════════════════════════════════════════════════════
# Formula Injection Detection
# ═══════════════════════════════════════════════════════════════════════════════

def detect_formula_injection(
    value: str,
) -> bool:
    """
    Check whether a string value starts with a spreadsheet formula prefix.

    Args:
        value: A single cell value from a CSV or Excel file.

    Returns:
        ``True`` if the value begins with a known formula prefix.
    """
    stripped = value.strip()
    return any(stripped.startswith(prefix) for prefix in _FORMULA_PREFIXES)


def scan_csv_for_formula_injection(
    content: str,
    *,
    max_cells_to_scan: int = 50_000,
    delimiter: str = ",",
) -> list[dict[str, int | str]]:
    """
    Scan raw CSV text for cells containing potential formula injection.

    This is a lightweight pre-parse scan — it does **not** replace full CSV
    parsing but catches the most common injection vectors before the data
    enters the processing pipeline.

    Args:
        content:            Raw CSV file content as a string.
        max_cells_to_scan:  Safety cap to prevent DoS on large files.
        delimiter:          Column separator character.

    Returns:
        A list of dicts ``{"row": int, "col": int, "value": str}`` describing
        flagged cells.  Empty list if no injection patterns found.
    """
    flagged: list[dict[str, int | str]] = []
    cells_scanned = 0

    for row_idx, line in enumerate(content.splitlines(), start=1):
        if cells_scanned >= max_cells_to_scan:
            break

        for col_idx, cell in enumerate(line.split(delimiter), start=1):
            cells_scanned += 1
            if cells_scanned > max_cells_to_scan:
                break

            cell_stripped = cell.strip().strip('"').strip("'")
            if cell_stripped and detect_formula_injection(cell_stripped):
                flagged.append({
                    "row": row_idx,
                    "col": col_idx,
                    "value": cell_stripped[:100],  # Truncate for safety
                })

    if flagged:
        _logger.warning(
            "formula_injection_detected",
            flagged_cells=len(flagged),
            sample=flagged[:5],
        )

    return flagged
