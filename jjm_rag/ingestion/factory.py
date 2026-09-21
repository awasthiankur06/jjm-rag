from __future__ import annotations

from dataclasses import dataclass, field
from hashlib import sha256
from pathlib import Path
from typing import Any


@dataclass
class CanonicalDocument:
    document_id: str
    filename: str
    original_path: str
    sha256: str
    source_format: str
    family: str
    report_type: str | None = None
    report_title: str | None = None
    format_code: str | None = None
    ingestion_status: str = "PENDING"
    quality_state: str | None = None
    production_included: bool = False


@dataclass
class CanonicalVersion:
    version_id: str
    document_id: str
    content_hash: str
    structural_fingerprint: str | None = None
    content_signature: str | None = None
    version_evidence: str = "INSUFFICIENT_VERSION_EVIDENCE"
    version_confidence: str = "UNKNOWN"
    snapshot_metadata: dict[str, Any] = field(default_factory=dict)


@dataclass
class SourceProvenance:
    provenance_id: str
    document_id: str
    page_number: int | None = None
    sheet_name: str | None = None
    table_name: str | None = None
    section_name: str | None = None
    row_index: int | None = None
    column_index: int | None = None
    cell_reference: str | None = None
    source_row_index: int | None = None
    source_col_index: int | None = None
    origin_cell_id: str | None = None


@dataclass
class StructuredObservation:
    record_id: str
    document_id: str
    table_name: str | None = None
    row_identity: str | None = None
    column_identity: str | None = None
    metric_name: str | None = None
    value_raw: str | None = None
    value_numeric: float | None = None
    unit: str | None = None
    geography_id: str | None = None
    reporting_id: str | None = None
    provenance_id: str | None = None


@dataclass
class CanonicalContentUnit:
    content_id: str
    document_id: str
    parent_content_id: str | None = None
    content_type: str = "text"
    section_name: str | None = None
    row_identity: str | None = None
    canonical_text: str = ""
    source_text: str | None = None
    provenance_id: str | None = None


def file_sha256(path: str | Path) -> str:
    digest = sha256()
    with Path(path).open("rb") as handle:
        for chunk in iter(lambda: handle.read(65536), b""):
            digest.update(chunk)
    return digest.hexdigest()


def canonical_document_from_source(path: str | Path, *, family: str = "unknown", ingestion_status: str = "PENDING", quality_state: str | None = None, production_included: bool = False) -> CanonicalDocument:
    source_path = Path(path)
    return CanonicalDocument(
        document_id=f"doc-{source_path.stem}",
        filename=source_path.name,
        original_path=str(source_path),
        sha256=file_sha256(source_path),
        source_format="unknown",
        family=family,
        ingestion_status=ingestion_status,
        quality_state=quality_state,
        production_included=production_included,
    )
