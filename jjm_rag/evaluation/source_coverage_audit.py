"""Generate and run provenance-backed, source-optional acceptance samples.

Each first-turn query is phrased as a user would ask it: it does *not* name a
file or report.  The acceptance contract permits either a direct, exact
source-backed answer, or a source/header clarification when the corpus is
ambiguous.  In the latter case the runner performs the second turn with the
same source-derived choice a user would click.  This prevents an internal
audit convenience from pretending that report names are required from users.
"""
from __future__ import annotations

import argparse
import json
from collections import defaultdict
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from jjm_rag.config import settings as _settings
from jjm_rag.persistence.database import get_database_session
from jjm_rag.production.postgres_store import PostgresEvidenceStore
from jjm_rag.production.rag import RagService

EXCLUDED = "Status of Pipe Water Supply in School (2).xls"


def _write(path: Path, data: dict[str, Any]) -> None:
    path.write_text(json.dumps(data, indent=2, ensure_ascii=False, default=str), encoding="utf-8")


def generate(cases_path: Path, per_source: int = 5) -> dict[str, Any]:
    conn = get_database_session()
    try:
        docs = conn.execute("SELECT document_id, filename, extracted_document_title, source_format FROM documents WHERE production_included=TRUE ORDER BY filename").fetchall()
        cases: list[dict[str, Any]] = []
        for doc in docs:
            records = conn.execute(
                """SELECT sr.record_id, sr.header_path, sr.value_raw, sr.provenance_id,
                          g.state_name, g.district_name
                   FROM structured_records sr LEFT JOIN geography_dimensions g ON g.geography_id=sr.geography_id
                   WHERE sr.document_id=? AND sr.value_numeric IS NOT NULL
                   ORDER BY CASE WHEN g.state_name IS NOT NULL OR g.district_name IS NOT NULL THEN 0 ELSE 1 END, sr.header_path, sr.record_id""",
                (doc["document_id"],),
            ).fetchall()
            selected: list[Any] = []
            seen_paths: set[str] = set()
            has_geography = any(row["state_name"] or row["district_name"] for row in records)
            for row in records:
                path = str(row["header_path"] or "")
                parts = json.loads(path) if path else []
                leaf = str(parts[-1] if parts else "").strip().lower()
                # Identity/ordinal cells remain in canonical storage but are
                # not answerable measures for this numeric acceptance suite.
                if leaf in {"id", "s.no.", "s no", "sr. no.", "sr no", "serial no."}:
                    continue
                if has_geography and not (row["state_name"] or row["district_name"]):
                    continue
                if path in seen_paths:
                    continue
                selected.append(row)
                seen_paths.add(path)
                if len(selected) == per_source:
                    break
            if selected:
                for ordinal, row in enumerate(selected, 1):
                    header = " → ".join(json.loads(row["header_path"]))
                    # The initial query intentionally has no filename, title,
                    # format code, or hidden source marker.  Header paths are
                    # source vocabulary, but retaining them here is necessary
                    # to ask an answerable multi-level table question.
                    query = header
                    if row["district_name"]:
                        query += f"\nDistrict: {row['district_name']}"
                    elif row["state_name"]:
                        query += f"\nState: {row['state_name']}"
                    continuation = f"{query}\nSelected source: {doc['filename']}\nSelected metric/header: {header}"
                    cases.append({"id": f"{doc['document_id']}-s{ordinal}", "kind": "structured", "query": query, "continuation_query": continuation, "document_id": doc["document_id"], "filename": doc["filename"], "record_id": row["record_id"], "provenance_id": row["provenance_id"], "header_path": row["header_path"], "value_raw": row["value_raw"]})
            else:
                pages = conn.execute("""SELECT c.content_id,c.provenance_id,p.page_number,c.canonical_text
                                      FROM canonical_content c LEFT JOIN provenance_records p ON p.provenance_id=c.provenance_id
                                      WHERE c.document_id=? AND c.canonical_text IS NOT NULL ORDER BY c.content_id LIMIT ?""", (doc["document_id"], per_source)).fetchall()
                for ordinal, row in enumerate(pages, 1):
                    # A short unique excerpt is the natural source-free PDF
                    # question; it does not require a user to know the title.
                    excerpt = " ".join(str(row["canonical_text"] or "").split()[:18])
                    query = f"What does the JJM material say about: {excerpt}?"
                    cases.append({"id": f"{doc['document_id']}-p{ordinal}", "kind": "canonical", "query": query, "continuation_query": f"{query}\nSelected source: {doc['filename']}", "document_id": doc["document_id"], "filename": doc["filename"], "content_id": row["content_id"], "provenance_id": row["provenance_id"]})
        artifact = {"artifact_type": "source_coverage_cases", "timestamp": datetime.now(timezone.utc).isoformat(), "per_source_target": per_source, "documents": len(docs), "cases": cases}
        _write(cases_path, artifact)
        return artifact
    finally:
        conn.close()


def run(cases_path: Path, output_path: Path, start: int, batch_size: int) -> dict[str, Any]:
    cases = json.loads(cases_path.read_text(encoding="utf-8"))["cases"]
    state = json.loads(output_path.read_text(encoding="utf-8")) if output_path.exists() else {"artifact_type": "source_coverage_results", "cases": {}}
    service = RagService(PostgresEvidenceStore(get_database_session()))
    try:
        for case in cases[start:start + batch_size]:
            if case["id"] in state["cases"]:
                continue
            first = service.query(case["query"], retrieval_only=True)
            response = first
            facts = response.structured_facts
            used_clarification = False
            if first.clarification is not None and case.get("continuation_query"):
                # The user has chosen a displayed source/header option.  The
                # continuation is only valid after the first turn explicitly
                # requested clarification; never use it to mask a wrong direct
                # answer from an ambiguous natural query.
                response = service.query(case["continuation_query"], retrieval_only=True)
                facts = response.structured_facts
                used_clarification = True
            if case["kind"] == "structured":
                matching = [fact for fact in facts if fact["metadata"].get("record_id") == case["record_id"] and fact["metadata"].get("provenance_id") == case["provenance_id"] and fact["metadata"].get("value_raw") == case["value_raw"]]
                passed = bool(matching)
                reason = "PASS" if passed else "expected source row/value/provenance absent"
            else:
                matching = [item for item in response.evidence if item.get("filename") == case["filename"] and item.get("metadata", {}).get("provenance_id") == case["provenance_id"]]
                passed = bool(matching)
                reason = "PASS" if passed else "expected canonical source/provenance absent"
            state["cases"][case["id"]] = {"id": case["id"], "kind": case["kind"], "query": case["query"], "continuation_query": case.get("continuation_query"), "expected": {key: case.get(key) for key in ("filename", "record_id", "content_id", "provenance_id", "header_path", "value_raw")}, "pass": passed, "reason": reason, "first_turn": {"route": first.retrieval.get("route"), "answer": first.answer, "clarification": first.clarification, "facts": first.structured_facts[:5], "evidence": first.evidence[:5]}, "used_clarification": used_clarification, "route": response.retrieval.get("route"), "answer": response.answer, "facts": facts[:5], "evidence": response.evidence[:5]}
            state["case_count_expected"] = len(cases)
            state["completed"] = len(state["cases"])
            state["complete"] = state["completed"] == len(cases)
            completed = list(state["cases"].values())
            state["passed"] = sum(item["pass"] for item in completed)
            state["failed"] = len(completed) - state["passed"]
            state["accuracy_if_complete"] = state["passed"] / len(completed) if completed else "NOT_EVALUABLE"
            _write(output_path, state)
    finally:
        service.evidence_store.connection.close()
    return state


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--cases", type=Path, default=Path("artifacts/source_coverage_cases.json"))
    parser.add_argument("--output", type=Path, default=Path("artifacts/source_coverage_results.json"))
    parser.add_argument("--generate", action="store_true")
    parser.add_argument("--start", type=int, default=0)
    parser.add_argument("--batch-size", type=int, default=10)
    args = parser.parse_args()
    if args.generate:
        artifact = generate(args.cases)
        print(json.dumps({"documents": artifact["documents"], "cases": len(artifact["cases"]) }))
    else:
        state = run(args.cases, args.output, args.start, args.batch_size)
        print(json.dumps({key: state.get(key) for key in ("completed", "case_count_expected", "passed", "failed", "complete")}))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
