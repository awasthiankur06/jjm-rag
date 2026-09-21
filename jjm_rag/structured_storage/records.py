from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any


@dataclass
class StructuredRecord:
    record_id: str
    source_document: str
    source_table: str | None = None
    source_section: str | None = None
    row_index: int | None = None
    geography: str | None = None
    metric_name: str | None = None
    value: Any = None
    value_type: str = "string"
    metadata: dict[str, Any] = field(default_factory=dict)
