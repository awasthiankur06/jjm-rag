from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path


@dataclass
class FileFormat:
    path: Path
    format_name: str
    confidence: float
    notes: list[str]


def detect_format(path: Path) -> FileFormat:
    """Detect likely format from binary header and content signatures."""
    if not path.exists():
        raise FileNotFoundError(f"File not found: {path}")

    suffix = path.suffix.lower()
    try:
        sample = path.read_bytes()[:256]
    except OSError:
        sample = b""

    if b"%PDF-" in sample[:16]:
        return FileFormat(path, "pdf", 0.98, ["PDF header detected"])

    if b"PK\x03\x04" in sample[:16] or suffix in {".xlsx", ".xlsm"}:
        return FileFormat(path, "xlsx", 0.95, ["ZIP-based spreadsheet detected"])

    if suffix in {".xls", ".csv"}:
        if b"<html" in sample.lower() or b"<table" in sample.lower() or b"<td" in sample.lower():
            return FileFormat(path, "html_table", 0.92, ["HTML-exported table content detected"])
        return FileFormat(path, "excel_binary_like", 0.75, ["Legacy spreadsheet-like file detected"])

    if suffix in {".html", ".htm"}:
        return FileFormat(path, "html", 0.9, ["HTML document detected"])

    if b"<html" in sample.lower() or b"<table" in sample.lower():
        return FileFormat(path, "html_table", 0.9, ["HTML/XML table signature detected"])

    return FileFormat(path, "unknown", 0.2, ["Signature insufficient to determine format"])
