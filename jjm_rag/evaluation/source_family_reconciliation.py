"""Evidence-based reconciliation for repeated report titles.

The raw corpus is immutable evidence.  This utility determines whether source
members sharing a source-derived title can be treated as one *logical* report
family in the canonical database.  It never deletes, edits, renames, or
re-ingests a raw document.
"""
from __future__ import annotations

import argparse
import json
import os
from collections import defaultdict
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


def _normalize(value: Any) -> str:
    return " ".join(str(value or "").casefold().split())


def _member_signature(rows: list[dict[str, Any]]) -> dict[str, Any]:
    """Return comparison keys without discarding raw values or provenance."""
    headers = {_normalize(row["header_path"]) for row in rows if _normalize(row["header_path"])}
    geography = {
        _normalize(row["district_name"] or row["state_name"])
        for row in rows
        if _normalize(row["district_name"] or row["state_name"]) not in {"", "total", "all state", "all district"}
    }
    values: dict[tuple[str, str], set[str]] = defaultdict(set)
    for row in rows:
        scope = _normalize(row["district_name"] or row["state_name"])
        header = _normalize(row["header_path"])
        if scope and header:
            values[(scope, header)].add(str(row["value_raw"] if row["value_raw"] is not None else ""))
    return {
        "headers": headers,
        "geography": geography,
        "values": values,
        "structured_record_count": len(rows),
    }


def _pair(left: dict[str, Any], right: dict[str, Any]) -> dict[str, Any]:
    left_signature = left["signature"]
    right_signature = right["signature"]
    common_headers = left_signature["headers"] & right_signature["headers"]
    same_schema = bool(left_signature["headers"]) and left_signature["headers"] == right_signature["headers"]
    geography_overlap = sorted(left_signature["geography"] & right_signature["geography"])
    common_keys = set(left_signature["values"]) & set(right_signature["values"])
    conflicts = sorted(
        f"{scope} | {header}"
        for scope, header in common_keys
        if left_signature["values"][(scope, header)] != right_signature["values"][(scope, header)]
    )
    if not left_signature["geography"] or not right_signature["geography"]:
        classification = "REQUIRES_REVIEW_NO_GEOGRAPHIC_KEYS"
    elif same_schema and not geography_overlap:
        classification = "COMPLEMENTARY_GEOGRAPHY_PARTITIONS"
    elif same_schema and geography_overlap and not conflicts:
        classification = "SAME_SCOPE_SAME_VALUES_POTENTIAL_DUPLICATE"
    elif same_schema and conflicts:
        classification = "CONFLICTING_SAME_SCOPE_SNAPSHOTS"
    else:
        classification = "STRUCTURAL_VARIANT"
    return {
        "left_filename": left["filename"],
        "right_filename": right["filename"],
        "same_header_schema": same_schema,
        "shared_header_count": len(common_headers),
        "left_header_count": len(left_signature["headers"]),
        "right_header_count": len(right_signature["headers"]),
        "geography_overlap": geography_overlap,
        "conflicting_key_count": len(conflicts),
        "conflicting_keys_sample": conflicts[:10],
        "classification": classification,
    }


def classify_members(title: str, members: list[dict[str, Any]]) -> dict[str, Any]:
    pairs = [_pair(members[index], members[next_index]) for index in range(len(members)) for next_index in range(index + 1, len(members))]
    classifications = {pair["classification"] for pair in pairs}
    if classifications == {"COMPLEMENTARY_GEOGRAPHY_PARTITIONS"}:
        decision = "LOGICALLY_CONSOLIDATE_ROWS_KEEP_RAW_SOURCES"
    elif "SAME_SCOPE_SAME_VALUES_POTENTIAL_DUPLICATE" in classifications:
        decision = "REVIEW_POTENTIAL_DUPLICATES_KEEP_RAW_SOURCES"
    elif "CONFLICTING_SAME_SCOPE_SNAPSHOTS" in classifications:
        decision = "KEEP_SEPARATE_CONFLICTING_SNAPSHOTS"
    else:
        decision = "KEEP_SEPARATE_PENDING_METADATA_OR_SCHEMA_REVIEW"
    return {
        "title": title,
        "member_count": len(members),
        "members": [
            {
                "filename": member["filename"],
                "sha256": member["sha256"],
                "format_code": member["format_code"],
                "structured_record_count": member["signature"]["structured_record_count"],
                "geography_count": len(member["signature"]["geography"]),
                "geography_sample": sorted(member["signature"]["geography"])[:8],
                "header_count": len(member["signature"]["headers"]),
            }
            for member in members
        ],
        "pairwise_comparisons": pairs,
        "consolidation_decision": decision,
        "raw_source_action": "RETAIN_IMMUTABLE",
    }


def reconcile(connection) -> dict[str, Any]:
    rows = connection.execute(
        """
        SELECT d.extracted_document_title, d.filename, d.sha256, d.format_code,
               sr.header_path, sr.value_raw, gd.state_name, gd.district_name
        FROM documents d
        JOIN structured_records sr ON sr.document_id = d.document_id
        LEFT JOIN geography_dimensions gd ON gd.geography_id = sr.geography_id
        WHERE d.production_included = TRUE
        ORDER BY d.extracted_document_title, d.filename, sr.record_id
        """
    ).fetchall()
    grouped: dict[str, dict[str, list[dict[str, Any]]]] = defaultdict(lambda: defaultdict(list))
    for row in rows:
        item = dict(row)
        grouped[str(item["extracted_document_title"] or item["filename"])][item["filename"]].append(item)
    families = []
    for title, by_filename in grouped.items():
        if len(by_filename) < 2:
            continue
        members = []
        for filename, member_rows in by_filename.items():
            first = member_rows[0]
            members.append({
                "filename": filename,
                "sha256": first["sha256"],
                "format_code": first["format_code"],
                "signature": _member_signature(member_rows),
            })
        families.append(classify_members(title, members))
    decisions = defaultdict(int)
    for family in families:
        decisions[family["consolidation_decision"]] += 1
    return {
        "artifact_type": "source_family_reconciliation",
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "scope": "production_included canonical PostgreSQL documents sharing source-derived titles",
        "raw_source_policy": "No source files are deleted, merged, renamed, or flattened by this audit.",
        "families": families,
        "summary": {
            "repeated_title_family_count": len(families),
            "decisions": dict(sorted(decisions.items())),
        },
    }


def main() -> None:
    parser = argparse.ArgumentParser(description="Reconcile repeated canonical report titles without modifying sources.")
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    # The application loads this same local development file without
    # overriding a deployment-provided environment variable.  The value is
    # used only to open the configured database and is never emitted.
    from dotenv import load_dotenv
    load_dotenv(Path(__file__).resolve().parents[2] / ".env", override=False)
    dsn = os.getenv("JJM_DATABASE_URL")
    if not dsn:
        raise SystemExit("JJM_DATABASE_URL is required; no fallback database is used for this audit.")
    import psycopg
    from psycopg.rows import dict_row
    with psycopg.connect(dsn, row_factory=dict_row) as connection:
        result = reconcile(connection)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(result, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")


if __name__ == "__main__":
    main()
