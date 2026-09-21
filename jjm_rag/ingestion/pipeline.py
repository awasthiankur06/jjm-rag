from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from jjm_rag.ingestion.discovery import discover_files
from jjm_rag.ingestion.format_detection import detect_format
from jjm_rag.ingestion.versioning import classify_content_relationship, compute_content_hash
from jjm_rag.models.canonical import Document
from jjm_rag.parsing.table_parsers import HtmlTableParser


@dataclass
class IngestionResult:
    source_path: str
    detected_format: str
    parser_name: str
    family: str
    content_hash: str
    version_relationship: str | None = None
    warnings: list[str] = field(default_factory=list)
    document: Document | None = None


class IngestionPipeline:
    """Phase 1 ingestion foundation for file discovery, format detection, parsing, and version metadata."""

    def __init__(self, corpus_root: str | Path):
        self.corpus_root = Path(corpus_root)
        self.parser_registry = {
            "html_table": HtmlTableParser(),
        }

    def run(self) -> list[IngestionResult]:
        results: list[IngestionResult] = []
        files = discover_files(self.corpus_root)
        for path in files:
            detection = detect_format(path)
            family = self.classify_family(path)
            parser = self.select_parser(detection.format_name)
            content_hash = compute_content_hash(path)
            document = None
            warnings: list[str] = []
            if parser is not None:
                document = parser.parse(path, family=family)
            if document is None:
                warnings.append("No parser produced a document model")
            result = IngestionResult(
                source_path=str(path),
                detected_format=detection.format_name,
                parser_name=getattr(parser, "parser_name", "unparsed"),
                family=family,
                content_hash=content_hash,
                warnings=warnings,
                document=document,
            )
            results.append(result)
        return results

    def classify_family(self, path: Path) -> str:
        name = path.name.lower()
        if "guideline" in name or path.suffix.lower() == ".pdf":
            return "policy"
        if "sanction" in name or "format d5" in name:
            return "sanction"
        if "status" in name or "progress" in name or "coverage" in name:
            return "report"
        if "template" in name or "format" in name:
            return "template"
        return "unknown"

    def select_parser(self, detected_format: str):
        if detected_format == "html_table":
            return self.parser_registry["html_table"]
        return None
