from __future__ import annotations

import argparse
import json
import os
import sqlite3
import uuid
from pathlib import Path

from jjm_rag.config.settings import PROJECT_ROOT
from jjm_rag.ingestion.canonical_persistence import parse_source, persist_canonical_source
from jjm_rag.ingestion.pipeline import IngestionPipeline
from jjm_rag.persistence.database import apply_migration, get_database_session, sqlite_connection
from jjm_rag.persistence.repositories import IngestionAuditRepository

EXCLUDED_FILENAME = "Status of Pipe Water Supply in School (2).xls"


def _ensure_schema(conn) -> None:
    migration_dir = PROJECT_ROOT / "db" / "migrations"
    for migration in sorted(migration_dir.glob("*.sql")):
        # Fresh SQLite test databases receive the complete initial schema. The
        # PostgreSQL-only ALTER migration exists for already-created databases.
        if isinstance(conn, sqlite3.Connection) and migration.name != "001_initial_schema.sql":
            continue
        apply_migration(conn, migration)


def _load_manifest(path: Path):
    return json.loads(path.read_text(encoding="utf-8"))


def _source_title_records() -> dict[str, dict]:
    review_path = PROJECT_ROOT / "artifacts" / "source_first_review.json"
    if not review_path.exists():
        return {}
    review = json.loads(review_path.read_text(encoding="utf-8"))
    return {record["original_filename"]: record for record in review.get("records", [])}


def _manifest_consolidation_guard(files: list[dict], title_records: dict[str, dict]) -> dict:
    """Block only unsafe automatic consolidation before any write occurs.

    Same-title inputs are deliberately *not* collapsed here: they may be
    geographic partitions or conflicting snapshots.  A byte-identical source,
    however, has no independent content identity and must be reviewed before a
    new production ingestion run can proceed.
    """
    eligible = [item for item in files if item.get("production_decision") != "EXCLUDED_CORRUPTED_SOURCE"]
    hashes: dict[str, list[str]] = {}
    titles: dict[str, list[str]] = {}
    for item in eligible:
        filename = str(item.get("filename") or "")
        digest = str(item.get("sha256") or "")
        if digest:
            hashes.setdefault(digest, []).append(filename)
        title = str(title_records.get(filename, {}).get("extracted_document_title") or "").strip()
        if title:
            titles.setdefault(title, []).append(filename)
    exact_duplicates = {digest: sorted(names) for digest, names in hashes.items() if len(names) > 1}
    repeated_titles = {title: sorted(names) for title, names in titles.items() if len(names) > 1}
    return {
        "exact_duplicate_hashes": exact_duplicates,
        "repeated_title_families_retained_for_reconciliation": repeated_titles,
        "automatic_logical_consolidation": "PROHIBITED_UNLESS_LIVE_RECONCILIATION_ALLOWLISTS_COMPLEMENTARY_PARTITIONS",
    }


def _build_summary(result: dict) -> dict:
    return {
        "files_discovered": result.get("files_discovered", 0),
        "files_eligible": result.get("files_eligible", 0),
        "files_excluded": result.get("files_excluded", 0),
        "files_ingested": result.get("files_ingested", 0),
        "already_ingested": result.get("already_ingested", 0),
        "failures": result.get("failures", 0),
        "record_counts": result.get("record_counts", 0),
        "observation_counts": result.get("observation_counts", 0),
        "content_unit_counts": result.get("content_unit_counts", 0),
        "structured_record_counts": result.get("structured_record_counts", 0),
        "provenance_counts": result.get("provenance_counts", 0),
        "geography_counts": result.get("geography_counts", 0),
        "reporting_counts": result.get("reporting_counts", 0),
        "audit_counts": result.get("audit_counts", 0),
    }


def _process_manifest(manifest_path: Path, *, dry_run: bool = False):
    manifest = _load_manifest(manifest_path)
    title_records = _source_title_records()
    files = manifest.get("files", [])
    guard = _manifest_consolidation_guard(files, title_records)
    if guard["exact_duplicate_hashes"]:
        raise ValueError(
            "Duplicate source SHA-256 values block ingestion; retain the sources for audit and resolve the duplication before retrying."
        )
    eligible = [entry for entry in files if entry.get("production_decision") != "EXCLUDED_CORRUPTED_SOURCE"]
    excluded = [entry for entry in files if entry.get("production_decision") == "EXCLUDED_CORRUPTED_SOURCE"]
    result = {
        "files_discovered": len(files),
        "files_eligible": len(eligible),
        "files_excluded": len(excluded),
        "files_ingested": 0,
        "already_ingested": 0,
        "failures": 0,
        "record_counts": 0,
        "observation_counts": 0,
        "content_unit_counts": 0,
        "structured_record_counts": 0,
        "provenance_counts": 0,
        "geography_counts": 0,
        "reporting_counts": 0,
        "audit_counts": 0,
    }
    if dry_run:
        return {"mode": "dry-run", "summary": _build_summary(result), "eligible_files": [entry["filename"] for entry in eligible], "consolidation_guard": guard}
    conn = (
        get_database_session()
        if os.getenv("JJM_DATABASE_URL")
        else sqlite_connection(os.getenv("JJM_SQLITE_PATH", str(PROJECT_ROOT / "tmp" / "phase6a.sqlite3")))
    )
    _ensure_schema(conn)
    execution_id = str(uuid.uuid4())
    pipeline = IngestionPipeline(Path(manifest.get("root", PROJECT_ROOT / "knowlade base files")))
    per_source = []
    for entry in eligible:
        filename = entry["filename"]
        try:
            entry = {**entry, **{key: value for key, value in title_records.get(filename, {}).items() if key in {"extracted_document_title", "title_provenance", "title_confidence"}}}
            path = Path(entry["absolute_path"])
            family = pipeline.classify_family(path)
            document = parse_source(path, family, entry)
            persisted = persist_canonical_source(conn, document, entry, execution_id)
            per_source.append({"filename": filename, "parser": document.source_metadata.parser_name, **persisted})
            if persisted["status"] == "SUCCESS":
                result["files_ingested"] += 1
            else:
                result["already_ingested"] += 1
            result["record_counts"] += int(persisted.get("records", 0))
            result["structured_record_counts"] += int(persisted.get("records", 0))
            result["observation_counts"] += int(persisted.get("observations", 0))
            result["content_unit_counts"] += int(persisted.get("content", 0))
            result["provenance_counts"] += int(persisted.get("provenance", 0))
            result["geography_counts"] += int(persisted.get("geography", 0))
            result["reporting_counts"] += int(persisted.get("reporting", 0))
            result["audit_counts"] += 1
        except Exception as error:
            result["failures"] += 1
            IngestionAuditRepository(conn).create({"audit_id": f"audit-{execution_id}-{entry.get('sha256')}", "document_id": None, "source_filename": filename, "source_sha256": entry.get("sha256"), "status": "FAILED", "reason": repr(error), "details": {"execution_id": execution_id}})
            per_source.append({"filename": filename, "status": "FAILED", "error": repr(error)})
    result["record_counts"] = result["structured_record_counts"]
    conn.close()
    return {"mode": "ingest", "execution_id": execution_id, "summary": _build_summary(result), "excluded": [entry["filename"] for entry in excluded], "per_source": per_source, "consolidation_guard": guard}


def main() -> int:
    parser = argparse.ArgumentParser(description="JJM production ingestion CLI")
    parser.add_argument("--manifest", default=str(PROJECT_ROOT / "artifacts" / "corpus_manifest_final.json"), help="Path to the corpus manifest JSON")
    parser.add_argument("--dry-run", action="store_true", help="Inspect manifest without persisting to database")
    parser.add_argument("--validation-only", action="store_true", help="Only validate manifest eligibility without ingestion")
    parser.add_argument("--summary", action="store_true", help="Print summary without committing changes")
    args = parser.parse_args()

    manifest_path = Path(args.manifest)
    if not manifest_path.exists():
        raise FileNotFoundError(manifest_path)
    result = _process_manifest(manifest_path, dry_run=args.dry_run or args.summary or args.validation_only)
    print(json.dumps(result, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
