from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path


@dataclass
class IngestionValidationReport:
    total_files: int = 0
    successfully_processed: int = 0
    failed_files: int = 0
    parser_selected_by_file: dict[str, str] = field(default_factory=dict)
    detected_format_by_file: dict[str, str] = field(default_factory=dict)
    family_by_file: dict[str, str] = field(default_factory=dict)
    warnings: list[str] = field(default_factory=list)
    potential_duplicates: list[str] = field(default_factory=list)
    potential_versions: list[str] = field(default_factory=list)
    extraction_quality: float = 0.0


def build_validation_report(results: list[object]) -> IngestionValidationReport:
    """Build a coarse ingestion quality report from the in-memory ingestion results."""
    report = IngestionValidationReport(total_files=len(results))
    for item in results:
        source_path = getattr(item, "source_path", "unknown")
        if getattr(item, "document", None) is not None:
            report.successfully_processed += 1
        else:
            report.failed_files += 1
            report.warnings.append(f"{source_path}: no document model produced")
        report.parser_selected_by_file[source_path] = getattr(item, "parser_name", "unparsed")
        report.detected_format_by_file[source_path] = getattr(item, "detected_format", "unknown")
        report.family_by_file[source_path] = getattr(item, "family", "unknown")
        if getattr(item, "warnings", None):
            report.warnings.extend(f"{source_path}: {warning}" for warning in item.warnings)

    report.extraction_quality = (report.successfully_processed / report.total_files) if report.total_files else 0.0
    return report
