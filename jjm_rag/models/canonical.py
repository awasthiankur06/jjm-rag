from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Any


@dataclass
class SourceMetadata:
    source_path: str
    filename: str
    file_size: int
    detected_format: str
    parser_name: str
    extraction_timestamp: str = field(default_factory=lambda: datetime.utcnow().isoformat(timespec="seconds"))
    content_hash: str | None = None
    last_modified: str | None = None


@dataclass
class Provenance:
    document_id: str
    source_path: str
    page_numbers: list[int] = field(default_factory=list)
    sheet_names: list[str] = field(default_factory=list)
    section_path: str | None = None
    table_name: str | None = None
    row_index: int | None = None
    cell_reference: str | None = None


@dataclass
class TableCell:
    row_index: int
    column_index: int
    value: Any
    raw_value: Any = None
    header: str | None = None
    header_path: list[str] | None = None


@dataclass
class Table:
    table_id: str
    name: str
    headers: list[str]
    rows: list[list[Any]]
    provenance: Provenance | None = None
    structured: dict | None = None
    header_paths: list[list[str]] | None = None


@dataclass
class Section:
    section_id: str
    title: str
    text: str
    page_numbers: list[int] = field(default_factory=list)
    tables: list[Table] = field(default_factory=list)
    provenance: Provenance | None = None


@dataclass
class Document:
    document_id: str
    source_path: str
    source_metadata: SourceMetadata
    family: str
    version_label: str | None = None
    version_relationship: str | None = None
    sections: list[Section] = field(default_factory=list)
    tables: list[Table] = field(default_factory=list)
    text_chunks: list[str] = field(default_factory=list)
    provenance: Provenance | None = None
