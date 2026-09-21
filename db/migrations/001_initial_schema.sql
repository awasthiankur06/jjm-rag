BEGIN;

CREATE TABLE IF NOT EXISTS documents (
    document_id TEXT PRIMARY KEY,
    filename TEXT NOT NULL,
    extracted_document_title TEXT,
    title_provenance TEXT,
    title_confidence TEXT,
    original_path TEXT,
    sha256 TEXT NOT NULL UNIQUE,
    source_format TEXT,
    family TEXT,
    report_type TEXT,
    report_title TEXT,
    format_code TEXT,
    ingestion_status TEXT NOT NULL DEFAULT 'PENDING',
    quality_state TEXT,
    production_included BOOLEAN NOT NULL DEFAULT FALSE,
    created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    ingested_at TIMESTAMP
);

CREATE TABLE IF NOT EXISTS document_versions (
    version_id TEXT PRIMARY KEY,
    document_id TEXT NOT NULL REFERENCES documents(document_id),
    content_hash TEXT NOT NULL,
    structural_fingerprint TEXT,
    content_signature TEXT,
    version_evidence TEXT NOT NULL DEFAULT 'INSUFFICIENT_VERSION_EVIDENCE',
    version_confidence TEXT NOT NULL DEFAULT 'UNKNOWN',
    snapshot_metadata JSONB,
    created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS provenance_records (
    provenance_id TEXT PRIMARY KEY,
    document_id TEXT NOT NULL REFERENCES documents(document_id),
    page_number INTEGER,
    sheet_name TEXT,
    table_name TEXT,
    section_name TEXT,
    row_index INTEGER,
    column_index INTEGER,
    cell_reference TEXT,
    source_row_index INTEGER,
    source_col_index INTEGER,
    origin_cell_id TEXT,
    created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS geography_dimensions (
    geography_id TEXT PRIMARY KEY,
    document_id TEXT NOT NULL REFERENCES documents(document_id),
    state_name TEXT,
    district_name TEXT,
    division_name TEXT,
    block_name TEXT,
    habitation_name TEXT,
    raw_label TEXT,
    created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS reporting_dimensions (
    reporting_id TEXT PRIMARY KEY,
    document_id TEXT NOT NULL REFERENCES documents(document_id),
    report_date TEXT,
    reporting_period TEXT,
    financial_year TEXT,
    snapshot_label TEXT,
    metric_name TEXT,
    format_code TEXT,
    report_family TEXT,
    created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS structured_records (
    record_id TEXT PRIMARY KEY,
    document_id TEXT NOT NULL REFERENCES documents(document_id),
    table_name TEXT,
    row_identity TEXT,
    column_identity TEXT,
    metric_name TEXT,
    value_raw TEXT,
    value_numeric NUMERIC,
    unit TEXT,
    geography_id TEXT REFERENCES geography_dimensions(geography_id),
    reporting_id TEXT REFERENCES reporting_dimensions(reporting_id),
    provenance_id TEXT REFERENCES provenance_records(provenance_id),
    header_path TEXT,
    created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS observations (
    observation_id TEXT PRIMARY KEY,
    document_id TEXT NOT NULL REFERENCES documents(document_id),
    record_id TEXT REFERENCES structured_records(record_id),
    metric_name TEXT,
    value_raw TEXT,
    value_numeric NUMERIC,
    unit TEXT,
    normalization_status TEXT NOT NULL DEFAULT 'RAW',
    provenance_id TEXT REFERENCES provenance_records(provenance_id),
    header_path TEXT,
    created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS canonical_content (
    content_id TEXT PRIMARY KEY,
    document_id TEXT NOT NULL REFERENCES documents(document_id),
    parent_content_id TEXT,
    content_type TEXT NOT NULL,
    section_name TEXT,
    row_identity TEXT,
    canonical_text TEXT NOT NULL,
    source_text TEXT,
    provenance_id TEXT REFERENCES provenance_records(provenance_id),
    created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS ingestion_audit (
    audit_id TEXT PRIMARY KEY,
    document_id TEXT REFERENCES documents(document_id),
    source_filename TEXT NOT NULL,
    source_sha256 TEXT,
    status TEXT NOT NULL,
    reason TEXT,
    details JSONB,
    created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX IF NOT EXISTS idx_documents_sha256 ON documents(sha256);
CREATE INDEX IF NOT EXISTS idx_documents_family ON documents(family);
CREATE INDEX IF NOT EXISTS idx_documents_report_type ON documents(report_type);
CREATE INDEX IF NOT EXISTS idx_documents_format_code ON documents(format_code);
CREATE INDEX IF NOT EXISTS idx_documents_ingestion_status ON documents(ingestion_status);
CREATE INDEX IF NOT EXISTS idx_versions_document_id ON document_versions(document_id);
CREATE INDEX IF NOT EXISTS idx_provenance_document_id ON provenance_records(document_id);
CREATE INDEX IF NOT EXISTS idx_geography_document_id ON geography_dimensions(document_id);
CREATE INDEX IF NOT EXISTS idx_reporting_document_id ON reporting_dimensions(document_id);
CREATE INDEX IF NOT EXISTS idx_structured_document_id ON structured_records(document_id);
CREATE INDEX IF NOT EXISTS idx_observations_document_id ON observations(document_id);
CREATE INDEX IF NOT EXISTS idx_content_document_id ON canonical_content(document_id);

COMMIT;
