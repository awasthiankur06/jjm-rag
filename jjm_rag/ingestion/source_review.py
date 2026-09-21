"""Non-destructive, source-first corpus audit for JJM documents.

This module is intentionally separate from production ingestion: it records what
the source actually exposes before metadata or parser decisions are trusted.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import re
from collections import Counter, defaultdict
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from bs4 import BeautifulSoup
from PyPDF2 import PdfReader


SUPPORTED = {".xls", ".xlsx", ".pdf"}
DATE_RE = re.compile(r"\b(?:\d{1,2}[/-]\d{1,2}[/-]\d{2,4}|\d{4}[/-]\d{1,2}[/-]\d{1,2})\b")
FY_RE = re.compile(r"\b(?:FY|Fin(?:ancial)?\s*Year)\s*[:=-]?\s*(\d{4}\s*[-/]\s*\d{2,4})\b", re.I)
FORMAT_RE = re.compile(r"\bFormat\s*[-:]?\s*([A-Z]\d+(?:\s*\([^)]+\))?)\b", re.I)


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as source:
        for block in iter(lambda: source.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def _clean(value: str | None) -> str:
    return re.sub(r"\s+", " ", value or "").strip()


def _html_title_review(path: Path) -> dict[str, Any]:
    soup = BeautifulSoup(path.read_text(encoding="utf-8", errors="replace"), "html.parser")
    candidates: list[dict[str, str]] = []
    for selector, confidence in (("#ReportHeading", "HIGH"), ("h1", "HIGH"), ("h2", "MEDIUM"), ("h3", "MEDIUM"), ("title", "MEDIUM")):
        for element in soup.select(selector):
            text = _clean(element.get_text(" ", strip=True))
            if len(text) >= 4:
                candidates.append({"text": text, "provenance": f"html:{selector}", "confidence": confidence})
    # A clearly labelled title cell is source-derived but weaker than a heading.
    for cell in soup.find_all(["th", "td"]):
        text = _clean(cell.get_text(" ", strip=True))
        if re.search(r"\b(?:report|status|format|progress|coverage|population|scheme)\b", text, re.I) and len(text) >= 12:
            candidates.append({"text": text, "provenance": "html:table-cell", "confidence": "LOW"})
            break
    unique: list[dict[str, str]] = []
    seen: set[str] = set()
    for candidate in candidates:
        key = candidate["text"].casefold()
        if key not in seen:
            seen.add(key)
            unique.append(candidate)
    selected = unique[0] if unique else None
    tables = soup.find_all("table")
    rows = soup.find_all("tr")
    return {
        "source_format": "html_exported_xls",
        "extracted_document_title": selected["text"] if selected else None,
        "title_confidence": selected["confidence"] if selected else "UNKNOWN",
        "title_provenance": selected["provenance"] if selected else None,
        "title_candidates": unique[:8],
        "structure": {"tables": len(tables), "rows": len(rows), "sheets": "NOT_APPLICABLE_HTML_EXPORT"},
        "sample_text": _clean(soup.get_text(" ", strip=True))[:4000],
    }


def _pdf_title_review(path: Path) -> dict[str, Any]:
    reader = PdfReader(str(path))
    metadata = reader.metadata or {}
    metadata_title = _clean(str(metadata.get("/Title") or ""))
    first_page_text = ""
    if reader.pages:
        try:
            first_page_text = _clean(reader.pages[0].extract_text() or "")
        except Exception:
            first_page_text = ""
    lines = [line for line in first_page_text.split("\n") if len(_clean(line)) >= 4]
    candidates: list[dict[str, str]] = []
    if metadata_title:
        candidates.append({"text": metadata_title, "provenance": "pdf:metadata:/Title", "confidence": "MEDIUM"})
    if lines:
        candidates.append({"text": _clean(lines[0]), "provenance": "pdf:page:1:first-text-line", "confidence": "LOW"})
    selected = candidates[0] if candidates else None
    return {
        "source_format": "pdf",
        "extracted_document_title": selected["text"] if selected else None,
        "title_confidence": selected["confidence"] if selected else "UNKNOWN",
        "title_provenance": selected["provenance"] if selected else None,
        "title_candidates": candidates,
        "structure": {"pages": len(reader.pages), "sheets": "NOT_APPLICABLE", "tables": "NOT_DETERMINED_BY_TITLE_AUDIT"},
        "sample_text": first_page_text[:4000],
    }


def _source_metadata(text: str) -> dict[str, Any]:
    return {
        "date_evidence": sorted(set(DATE_RE.findall(text)))[:20],
        "financial_year_evidence": sorted(set(FY_RE.findall(text)))[:20],
        "format_code_evidence": sorted(set(FORMAT_RE.findall(text)))[:20],
        "geography_evidence": "NOT_DETERMINED_BY_TITLE_AUDIT",
        "report_family_evidence": "NOT_DETERMINED_BY_TITLE_AUDIT",
        "version_evidence": "INSUFFICIENT_EVIDENCE: filename suffixes deliberately ignored",
    }


def review_corpus(corpus_root: Path, output_path: Path) -> dict[str, Any]:
    records: list[dict[str, Any]] = []
    for path in sorted(item for item in corpus_root.iterdir() if item.is_file() and item.suffix.lower() in SUPPORTED):
        review = _pdf_title_review(path) if path.suffix.lower() == ".pdf" else _html_title_review(path)
        text = review.pop("sample_text")
        record = {
            "original_filename": path.name,
            "physical_path": str(path.resolve()),
            "sha256": _sha256(path),
            "size_bytes": path.stat().st_size,
            **review,
            **_source_metadata(text),
            "structured_record_extraction_potential": "YES" if review["structure"].get("tables", 0) not in (0, "NOT_DETERMINED_BY_TITLE_AUDIT") else "UNKNOWN",
            "narrative_content_extraction_potential": "YES" if text else "UNKNOWN",
            "production_ingestion_decision": "PENDING_SOURCE_QUALITY_REVIEW",
        }
        records.append(record)
    by_hash: dict[str, list[str]] = defaultdict(list)
    for record in records:
        by_hash[record["sha256"]].append(record["original_filename"])
    for record in records:
        duplicates = by_hash[record["sha256"]]
        record["duplicate_evidence"] = {"same_sha256_files": duplicates, "exact_duplicate": len(duplicates) > 1}
    result = {
        "artifact_type": "source_first_title_and_structure_review",
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "corpus_root": str(corpus_root.resolve()),
        "source_count": len(records),
        "title_confidence_counts": dict(Counter(record["title_confidence"] for record in records)),
        "records": records,
        "method_limits": [
            "This audit records source-derived title candidates and their provenance; it does not use filenames as titles.",
            "HTML-exported XLS files are inspected as their actual HTML format; binary workbook sheets require a dedicated workbook parser.",
            "PDF titles are limited to embedded metadata and first-page text in this pass; scanned PDFs may have unknown titles without validated OCR.",
        ],
    }
    output_path.write_text(json.dumps(result, indent=2, ensure_ascii=False), encoding="utf-8")
    return result


def main() -> int:
    parser = argparse.ArgumentParser(description="Create a non-destructive source-first corpus review")
    parser.add_argument("--corpus", type=Path, default=Path("knowlade base files"))
    parser.add_argument("--output", type=Path, default=Path("artifacts/source_first_review.json"))
    args = parser.parse_args()
    result = review_corpus(args.corpus, args.output)
    print(json.dumps({"source_count": result["source_count"], "title_confidence_counts": result["title_confidence_counts"]}, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
