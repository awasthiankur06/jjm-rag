BEGIN;

ALTER TABLE documents ADD COLUMN IF NOT EXISTS extracted_document_title TEXT;
ALTER TABLE documents ADD COLUMN IF NOT EXISTS title_provenance TEXT;
ALTER TABLE documents ADD COLUMN IF NOT EXISTS title_confidence TEXT;

COMMIT;
