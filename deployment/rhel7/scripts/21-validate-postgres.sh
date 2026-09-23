#!/usr/bin/env bash
set -euo pipefail

: "${JJM_DATABASE_URL:?Set JJM_DATABASE_URL only in the current protected shell or service environment.}"

psql "$JJM_DATABASE_URL" --set=ON_ERROR_STOP=1 --tuples-only --no-align <<'SQL'
SELECT 'documents=' || COUNT(*) FROM documents;
SELECT 'document_versions=' || COUNT(*) FROM document_versions;
SELECT 'structured_records=' || COUNT(*) FROM structured_records;
SELECT 'observations=' || COUNT(*) FROM observations;
SELECT 'canonical_content=' || COUNT(*) FROM canonical_content;
SELECT 'provenance_records=' || COUNT(*) FROM provenance_records;
SELECT 'excluded_source_rows=' || COUNT(*)
FROM documents
WHERE filename = 'Status of Pipe Water Supply in School (2).xls';
SELECT 'not_ingested_documents=' || COUNT(*)
FROM documents
WHERE ingestion_status IS DISTINCT FROM 'INGESTED';
SQL

excluded=$(psql "$JJM_DATABASE_URL" --set=ON_ERROR_STOP=1 --tuples-only --no-align -c "SELECT COUNT(*) FROM documents WHERE filename = 'Status of Pipe Water Supply in School (2).xls';")
if [[ "$excluded" != 0 ]]; then
  echo 'FAILED: excluded corrupted source is present in documents.' >&2
  exit 1
fi
echo 'PostgreSQL validation passed: excluded corrupted source is absent.'
