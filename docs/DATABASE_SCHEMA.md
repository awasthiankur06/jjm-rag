# Database schema

## Overview

The canonical PostgreSQL schema is intentionally normalized and explicitly domain-aware to the JJM corpus. It is designed to store source identity, provenance, geographic context, reporting metadata, structured observations, and canonical content without depending on a vector database.

## Tables

### documents

Stores a unique physical-source record for each versioned source file.

Required fields:

- `document_id`
- `filename`
- `sha256`
- `ingestion_status`
- `production_included`

### document_versions

Stores version-level evidence and snapshot metadata. This table represents snapshots independently from filename conventions and preserves `INSUFFICIENT_VERSION_EVIDENCE` when ordering cannot be established.

### provenance_records

Stores the exact source location chain for facts and citations.

### geography_dimensions

Stores normalized `state`, `district`, `division`, `block`, and `habitation` values when available.

### reporting_dimensions

Stores report-level metadata such as date, reporting period, financial year, and format details.

### structured_records

Stores table-derived numeric and structured observations with raw value preservation.

### observations

Stores normalized observation-level records while preserving their raw values and provenance.

### canonical_content

Stores normalized content units for retrieval and downstream analysis.

### ingestion_audit

Stores each file's ingestion result and failure reasons.

## Migration

The initial migration is in [db/migrations/001_initial_schema.sql](../db/migrations/001_initial_schema.sql).

The migration is designed to run against a clean empty database and uses deterministic, transaction-safe DDL with selective indexes only for likely production access paths.
