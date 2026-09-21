from __future__ import annotations

import hashlib
import json
import re
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from jjm_rag.ingestion.format_detection import detect_format
from jjm_rag.ingestion.versioning import compute_content_hash
from jjm_rag.models.canonical import Document, Table
from jjm_rag.normalization.canonicalizer import normalize_document
from jjm_rag.parsing.pdf_parsers import PdfParser
from jjm_rag.parsing.table_parsers import HtmlTableParser
from jjm_rag.persistence.database import transaction
from jjm_rag.persistence.repositories import (
    CanonicalContentRepository,
    DocumentRepository,
    GeographyRepository,
    IngestionAuditRepository,
    ObservationRepository,
    ProvenanceRepository,
    ReportingRepository,
    StructuredRecordRepository,
    VersionRepository,
)

_EXCLUDED = "Status of Pipe Water Supply in School (2).xls"
_NUMBER = re.compile(r"^-?\s*\d[\d,]*(?:\.\d+)?\s*%?$")
_DATE = re.compile(r"^\d{1,2}[/-]\d{1,2}[/-]\d{2,4}$|^\d{4}[/-]\d{1,2}[/-]\d{1,2}$")
_FORMAT = re.compile(r"\bFormat\s*[-:]?\s*([A-Z0-9]+(?:\s*\([A-Za-z0-9]+\))*)", re.I)
_NON_METRIC_HEADER = re.compile(r"^(?:col_\d+|s\.?\s*no\.?|serial(?:\s+no\.?)?)$", re.I)
_STATE_DIMENSION_HEADERS = {"state", "state name", "state ut", "state union territory"}


def _stable(prefix: str, *values: object) -> str:
    payload = "|".join(str(value or "") for value in values)
    return f"{prefix}-{hashlib.sha256(payload.encode('utf-8')).hexdigest()[:32]}"


def _text(value: Any) -> str:
    return str(value).strip() if value is not None else ""


def _typed_value(value: str) -> tuple[Any, str, str | None]:
    raw = _text(value)
    if not raw or raw in {"-", "--", "---", "----", "NA", "N/A"}:
        return None, "RAW_AMBIGUOUS", None
    if _DATE.match(raw):
        return None, "RAW_DATE", raw
    if _NUMBER.match(raw.replace(" ", "")):
        unit = "%" if raw.endswith("%") else None
        numeric = raw.replace(",", "").replace("%", "").strip()
        try:
            return float(numeric), "PARSED_NUMERIC", unit
        except ValueError:
            pass
    return None, "RAW", None


def _metadata(text: str, filename: str, entry: dict[str, Any]) -> dict[str, Any]:
    format_match = _FORMAT.search(text)
    date_match = re.search(r"\b(?:\d{1,2}[/-]\d{1,2}[/-]\d{2,4}|\d{4}[/-]\d{1,2}[/-]\d{1,2})\b", text)
    year_match = re.search(r"\b(?:FinYear|Financial Year|Sanction Year|Fin Year)\s*[:=-]\s*([^,\n]+)", text, re.I)
    # Web-exported tables often place the selected state above the table,
    # rather than repeating it in every Division/District row.  This is
    # source text, not filename inference.  Stop before the first table
    # dimension/header so "State: Maharashtra S. No." stays Maharashtra.
    state_match = re.search(
        r"\bState\s*:\s*([A-Za-z][A-Za-z .&()'\-]*?)(?=\s*,|\s+(?:S(?:r)?\.?\s*No\.?|Division|District|Block|Category|Format|School)\b|$)",
        text,
        re.I,
    )
    source_state = state_match.group(1).strip() if state_match else None
    if source_state and source_state.casefold() in {"all state", "all states"}:
        source_state = None
    return {
        # A filename is physical identity, not source metadata. Only an audited,
        # sufficiently reliable internal title may become the logical title.
        "report_title": entry.get("extracted_document_title") if entry.get("title_confidence") in {"HIGH", "MEDIUM"} else None,
        "format_code": entry.get("format_code") or (format_match.group(1).strip() if format_match else None),
        "report_date": entry.get("date") or (date_match.group(0) if date_match else None),
        "financial_year": entry.get("financial_year") or (year_match.group(1).strip() if year_match else None),
        "state": entry.get("state") or source_state,
        "district": entry.get("district"),
        "division": entry.get("division"),
        "family": _family_from_source_text(text),
    }


def _family_from_source_text(text: str) -> str:
    """Classify only from extracted source text, never filename conventions."""
    lowered = text.lower()
    if "guideline" in lowered or "operational guideline" in lowered:
        return "policy"
    if "sanction order" in lowered:
        return "sanction"
    if "format" in lowered:
        return "template"
    if any(term in lowered for term in ("status", "progress", "coverage", "report")):
        return "report"
    return "unknown"


def parse_source(path: Path, family: str, entry: dict[str, Any]) -> Document:
    detection = detect_format(path)
    if detection.format_name == "html_table":
        document = HtmlTableParser().parse(path, family=family)
    elif detection.format_name == "pdf":
        document = PdfParser().parse(path, family=family, ocr_artifact=entry.get("ocr_artifact"))
    else:
        raise ValueError(f"No canonical parser for {detection.format_name}: {path.name}")
    document.source_metadata.content_hash = compute_content_hash(path)
    document.family = _family_from_source_text("\n".join(document.text_chunks + [section.text for section in document.sections]))
    return normalize_document(document)


def _geography_for_row(headers: list[str], row: list[Any], metadata: dict[str, Any], header_paths: list[list[str]] | None = None) -> dict[str, str | None]:
    values = {"state": metadata.get("state"), "district": metadata.get("district"), "division": metadata.get("division")}
    for column_index, (header, value) in enumerate(zip(headers, row)):
        # Geography must be taken only from an actual dimension column.  A
        # substring check corrupted rows when metrics such as "State Referral
        # Lab" or "district-level labs" overwrote the State/UT cell.
        name = " ".join(_text(header).lower().replace("/", " ").split())
        candidate = _text(value)
        path = header_paths[column_index] if header_paths and column_index < len(header_paths) else [header]
        normalized_path = [" ".join(_text(part).lower().replace("/", " ").split()) for part in path if _text(part)]
        dimension_labels = _STATE_DIMENSION_HEADERS | {"district", "district name", "division", "division name"}
        # A nested leaf called "State" may be a metric, not a geography
        # dimension. Only an exact source dimension heading is authoritative.
        is_dimension_heading = len(normalized_path) == 1 and normalized_path[0] in dimension_labels
        # A dimension is a label, never a serial number, metric value, or
        # aggregate row marker.  Preserve the raw cell separately as a record,
        # but do not corrupt dimension filters with it.
        valid_dimension = candidate and not re.fullmatch(r"[\d,.]+%?", candidate) and candidate.lower() not in {"total", "grand total", "all"}
        # Legacy report exports use several equally semantic labels for the
        # state dimension.  Treat these exact normalized labels alike; do not
        # use a substring match because metric headings often contain the word
        # "state" (for example, "State Referral Lab").
        if is_dimension_heading and name in _STATE_DIMENSION_HEADERS and valid_dimension:
            values["state"] = candidate
        elif is_dimension_heading and name in {"district", "district name"} and valid_dimension:
            values["district"] = candidate
        elif is_dimension_heading and name in {"division", "division name"} and valid_dimension:
            values["division"] = candidate
    return values


def backfill_row_geography(conn, document_ids: set[str] | None = None) -> dict[str, int]:
    """Repair legacy state-row links without recreating source content.

    Older canonical rows retained a ``State Name`` cell but did not recognize
    that exact heading as a geography dimension.  The source row identity is
    stable, so its state cell is the authoritative, source-grounded dimension
    for every metric in that same row.  This function is deliberately limited
    to exact state-dimension headings and valid label values; it never infers a
    state from filenames or values in metric columns.
    """
    clauses = ["LOWER(sr.metric_name) IN (?, ?, ?, ?)"]
    params: list[Any] = sorted(_STATE_DIMENSION_HEADERS)
    if document_ids:
        placeholders = ", ".join("?" for _ in document_ids)
        clauses.append(f"sr.document_id IN ({placeholders})")
        params.extend(sorted(document_ids))
    rows = conn.execute(
        f"""SELECT sr.document_id, sr.table_name, sr.row_identity, sr.value_raw, sr.header_path
            FROM structured_records sr
            WHERE {' AND '.join(clauses)}
            ORDER BY sr.document_id, sr.table_name, sr.row_identity""",
        tuple(params),
    ).fetchall()
    geography_repo = GeographyRepository(conn)
    geography_ids: dict[tuple[str, str], str] = {}
    repaired_rows = 0
    repaired_records = 0
    skipped_labels = 0
    for row in rows:
        try:
            path = json.loads(row["header_path"]) if isinstance(row["header_path"], str) else row["header_path"]
        except (TypeError, json.JSONDecodeError):
            path = None
        normalized_path = [" ".join(_text(part).lower().replace("/", " ").split()) for part in path or [] if _text(part)]
        if len(normalized_path) != 1 or normalized_path[0] not in _STATE_DIMENSION_HEADERS:
            continue
        state = _text(row["value_raw"])
        if not state or re.fullmatch(r"[\d,.]+%?", state) or state.lower() in {"total", "grand total", "all"}:
            skipped_labels += 1
            continue
        document_id = str(row["document_id"])
        key = (document_id, state)
        geography_id = geography_ids.get(key)
        if geography_id is None:
            geography_id = _stable("geo", document_id, state, "", "")
            geography_repo.upsert({
                "geography_id": geography_id,
                "document_id": document_id,
                "state_name": state,
                "district_name": None,
                "division_name": None,
                "block_name": None,
                "habitation_name": None,
                "raw_label": state,
            })
            geography_ids[key] = geography_id
        updated = conn.execute(
            """UPDATE structured_records
               SET geography_id = ?
               WHERE document_id = ? AND table_name = ? AND row_identity = ?
                 AND (geography_id IS NULL OR geography_id <> ?)""",
            (geography_id, document_id, row["table_name"], row["row_identity"], geography_id),
        )
        # Both SQLite and psycopg expose rowcount for this DML statement.
        repaired_records += max(0, int(getattr(updated, "rowcount", 0) or 0))
        repaired_rows += 1
    return {
        "source_rows": len(rows),
        "rows_reconciled": repaired_rows,
        "structured_records_relinked": repaired_records,
        "invalid_or_total_labels_skipped": skipped_labels,
        "geography_dimensions_upserted": len(geography_ids),
    }


def persist_canonical_source(conn, document: Document, entry: dict[str, Any], execution_id: str) -> dict[str, int | str]:
    """Persist one source atomically so a failed parse/write cannot be INGESTED."""
    with transaction(conn) as session:
        return _persist_canonical_source(session, document, entry, execution_id)


def replace_canonical_source(conn, document: Document, entry: dict[str, Any], execution_id: str) -> dict[str, int | str]:
    """Atomically replace one known source's derived canonical rows.

    This is deliberately narrower than a corpus rebuild. It is for a proven
    parser defect where the content hash/source identity is unchanged but its
    derived rows must be regenerated. All dependent rows are removed in FK
    order and the replacement is committed only if parsing and persistence
    both succeed.
    """
    document_hash = document.source_metadata.content_hash or compute_content_hash(document.source_path)
    with transaction(conn) as session:
        existing = DocumentRepository(session).get_by_sha256(document_hash)
        if existing:
            document_id = existing["document_id"]
            # These tables all contain source-derived rows. Do not touch any
            # other document; every predicate is the exact stable document id.
            for table in ("observations", "structured_records", "canonical_content", "provenance_records", "geography_dimensions", "reporting_dimensions", "document_versions", "ingestion_audit"):
                session.execute(f"DELETE FROM {table} WHERE document_id = ?", (document_id,))
            session.execute("DELETE FROM documents WHERE document_id = ?", (document_id,))
        return _persist_canonical_source(session, document, entry, execution_id)


def _persist_canonical_source(conn, document: Document, entry: dict[str, Any], execution_id: str) -> dict[str, int | str]:
    now = datetime.now(timezone.utc).isoformat()
    document_hash = document.source_metadata.content_hash or compute_content_hash(document.source_path)
    document_id = _stable("doc", document_hash)
    document_repo = DocumentRepository(conn)
    existing = document_repo.get_by_sha256(document_hash)
    if existing:
        IngestionAuditRepository(conn).create({"audit_id": _stable("audit", execution_id, document_hash), "document_id": existing["document_id"], "source_filename": document.source_metadata.filename, "source_sha256": document_hash, "status": "ALREADY_INGESTED", "reason": "Logical document identity already exists", "details": {"execution_id": execution_id, "parser": document.source_metadata.parser_name}})
        return {"status": "ALREADY_INGESTED", "document_id": existing["document_id"], "records": 0, "observations": 0, "content": 0, "provenance": 0, "geography": 0, "reporting": 0}

    # HTML report parameters (for example ``State: Maharashtra``) are often
    # retained in the parsed section text rather than `text_chunks`.  Include
    # both source-derived representations before extracting metadata.
    all_text = "\n".join(document.text_chunks + [section.text for section in document.sections])
    metadata = _metadata(all_text, document.source_metadata.filename, entry)
    document_repo.create({
        "document_id": document_id,
        "filename": document.source_metadata.filename,
        "extracted_document_title": metadata["report_title"],
        "title_provenance": entry.get("title_provenance"),
        "title_confidence": entry.get("title_confidence", "UNKNOWN"),
        "original_path": document.source_path,
        "sha256": document_hash,
        "source_format": document.source_metadata.detected_format,
        "family": document.family,
        "report_type": metadata["family"],
        "report_title": metadata["report_title"],
        "format_code": metadata["format_code"],
        "ingestion_status": "INGESTED",
        "quality_state": entry.get("quality_state"),
        "production_included": True,
    })
    VersionRepository(conn).create({
        "version_id": _stable("version", document_hash),
        "document_id": document_id,
        "content_hash": document_hash,
        "structural_fingerprint": entry.get("struct_fingerprint"),
        "content_signature": _stable("content", all_text[:10000]),
        "version_evidence": "INSUFFICIENT_VERSION_EVIDENCE",
        "version_confidence": "UNKNOWN",
        "snapshot_metadata": {"source": "canonical_parser", "filename": document.source_metadata.filename},
    })

    geography_repo = GeographyRepository(conn)
    reporting_repo = ReportingRepository(conn)
    provenance_repo = ProvenanceRepository(conn)
    records_repo = StructuredRecordRepository(conn)
    observations_repo = ObservationRepository(conn)
    content_repo = CanonicalContentRepository(conn)
    geography_ids: dict[tuple[str, str, str], str] = {}
    reporting_id = None
    if any(metadata.get(key) for key in ("report_date", "financial_year", "format_code")):
        reporting_id = _stable("reporting", document_id, metadata.get("report_date"), metadata.get("financial_year"), metadata.get("format_code"))
        reporting_repo.upsert({"reporting_id": reporting_id, "document_id": document_id, "report_date": metadata.get("report_date"), "financial_year": metadata.get("financial_year"), "format_code": metadata.get("format_code"), "report_family": metadata.get("family"), "snapshot_label": None, "reporting_period": None, "metric_name": None})

    counts = {"records": 0, "observations": 0, "content": 0, "provenance": 0, "geography": 0, "reporting": 1 if reporting_id else 0}
    persisted_table_ids: set[str] = set()
    for section in document.sections:
        section_prov_id = _stable("prov", document_id, section.section_id)
        provenance_repo.create({"provenance_id": section_prov_id, "document_id": document_id, "page_number": section.page_numbers[0] if section.page_numbers else None, "section_name": section.title})
        counts["provenance"] += 1
        section_content_id = _stable("content", document_id, section.section_id)
        content_repo.insert({"content_id": section_content_id, "document_id": document_id, "content_type": "section" if section.tables else "page", "section_name": section.title, "canonical_text": section.text or section.title, "source_text": section.text, "provenance_id": section_prov_id})
        counts["content"] += 1
        for table in section.tables:
            if table.table_id in persisted_table_ids:
                continue
            persisted_table_ids.add(table.table_id)
            table_counts = _persist_table(conn, document_id, table, section_content_id, metadata, reporting_id, geography_ids, geography_repo, provenance_repo, records_repo, observations_repo, content_repo)
            for key, value in table_counts.items():
                counts[key] += value
    for table in document.tables:
        if table.table_id in persisted_table_ids:
            continue
        persisted_table_ids.add(table.table_id)
        table_counts = _persist_table(conn, document_id, table, None, metadata, reporting_id, geography_ids, geography_repo, provenance_repo, records_repo, observations_repo, content_repo)
        for key, value in table_counts.items():
            counts[key] += value
    IngestionAuditRepository(conn).create({"audit_id": _stable("audit", execution_id, document_hash), "document_id": document_id, "source_filename": document.source_metadata.filename, "source_sha256": document_hash, "status": "SUCCESS", "reason": None, "details": {"execution_id": execution_id, "parser": document.source_metadata.parser_name, "counts": counts, "completed_at": now}})
    return {"status": "SUCCESS", "document_id": document_id, **counts}


def _persist_table(conn, document_id, table: Table, parent_content_id, metadata, reporting_id, geography_ids, geography_repo, provenance_repo, records_repo, observations_repo, content_repo):
    counts = {"records": 0, "observations": 0, "content": 0, "provenance": 0, "geography": 0}
    table_prov_id = _stable("prov", document_id, table.table_id)
    provenance_repo.create({"provenance_id": table_prov_id, "document_id": document_id, "table_name": table.name})
    counts["provenance"] += 1
    table_content_id = _stable("content", document_id, table.table_id)
    content_repo.insert({"content_id": table_content_id, "document_id": document_id, "parent_content_id": parent_content_id, "content_type": "table", "canonical_text": " | ".join(table.headers), "source_text": " | ".join(table.headers), "provenance_id": table_prov_id})
    counts["content"] += 1
    data_start_row = int((table.structured or {}).get("data_start_row", 0))
    for row_index, row in enumerate(table.rows):
        source_row_index = data_start_row + row_index
        if not any(_text(value) for value in row):
            continue
        if row_index == 0 and [_text(value) for value in row] == [_text(value) for value in table.headers]:
            continue
        header_paths = (table.structured or {}).get("header_paths") if table.structured else None
        geo = _geography_for_row(table.headers, row, metadata, header_paths)
        geo_key = (_text(geo.get("state")), _text(geo.get("district")), _text(geo.get("division")))
        geography_id = None
        if any(geo_key):
            geography_id = geography_ids.get(geo_key)
            if geography_id is None:
                geography_id = _stable("geo", document_id, *geo_key)
                geography_repo.upsert({"geography_id": geography_id, "document_id": document_id, "state_name": geo.get("state"), "district_name": geo.get("district"), "division_name": geo.get("division"), "block_name": None, "habitation_name": None, "raw_label": " | ".join(value for value in geo_key if value)})
                geography_ids[geo_key] = geography_id
                counts["geography"] += 1
        row_content_id = _stable("content", document_id, table.table_id, source_row_index)
        row_text = " | ".join(_text(value) for value in row)
        row_prov_id = _stable("prov", document_id, table.table_id, source_row_index)
        provenance_repo.create({"provenance_id": row_prov_id, "document_id": document_id, "table_name": table.name, "row_index": source_row_index})
        content_repo.insert({"content_id": row_content_id, "document_id": document_id, "parent_content_id": table_content_id, "content_type": "row", "row_identity": str(source_row_index), "canonical_text": row_text, "source_text": row_text, "provenance_id": row_prov_id})
        counts["provenance"] += 1
        counts["content"] += 1
        for column_index, value in enumerate(row):
            raw = _text(value)
            if not raw:
                continue
            header = table.headers[column_index] if column_index < len(table.headers) else "value"
            # An absent heading or a serial-number heading has no fact
            # semantics.  Keep the source row unchanged in canonical content,
            # with its row provenance, but do not expose the cell as a
            # structured metric named ``col_1`` (or equivalent).
            if _NON_METRIC_HEADER.fullmatch(_text(header)):
                continue
            header_paths = (table.structured or {}).get("header_paths") if table.structured else None
            header_path = header_paths[column_index] if header_paths and column_index < len(header_paths) else [header]
            numeric, normalization_status, unit = _typed_value(raw)
            if unit is None and numeric is not None and "%" in _text(header):
                unit = "%"
            cell_prov_id = _stable("prov", document_id, table.table_id, source_row_index, column_index)
            provenance_repo.create({"provenance_id": cell_prov_id, "document_id": document_id, "table_name": table.name, "row_index": source_row_index, "column_index": column_index, "cell_reference": f"R{source_row_index + 1}C{column_index + 1}", "source_row_index": source_row_index, "source_col_index": column_index})
            counts["provenance"] += 1
            record_id = _stable("record", document_id, table.table_id, source_row_index, column_index)
            record_payload = {"record_id": record_id, "document_id": document_id, "table_name": table.name, "row_identity": str(source_row_index), "column_identity": header, "metric_name": header, "value_raw": raw, "value_numeric": numeric, "unit": unit, "geography_id": geography_id, "reporting_id": reporting_id, "provenance_id": cell_prov_id, "header_path": json.dumps(header_path, ensure_ascii=False)}
            records_repo.insert(record_payload)
            observations_repo.insert({"observation_id": _stable("observation", record_id), "document_id": document_id, "record_id": record_id, "metric_name": header, "value_raw": raw, "value_numeric": numeric, "unit": unit, "normalization_status": normalization_status, "provenance_id": cell_prov_id, "header_path": json.dumps(header_path, ensure_ascii=False)})
            counts["records"] += 1
            counts["observations"] += 1
    return counts
