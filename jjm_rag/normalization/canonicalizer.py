from __future__ import annotations

from pathlib import Path
from typing import Any

from jjm_rag.models.canonical import Document, Section, SourceMetadata, Table


def normalize_document(doc: Document) -> Document:
    """Ensure the canonical document keeps the source metadata and table metadata intact."""
    doc.text_chunks = build_text_chunks(doc)
    return doc


def build_text_chunks(doc: Document) -> list[str]:
    chunks: list[str] = []
    for section in doc.sections:
        if section.text.strip():
            chunks.append(section.text.strip())
        for table in section.tables:
            if table.headers:
                chunks.append(" | ".join(table.headers))
            for row in table.rows:
                if row:
                    chunks.append(" | ".join(str(cell) for cell in row if cell is not None))
    for table in doc.tables:
        if table.headers:
            chunks.append(" | ".join(table.headers))
        for row in table.rows:
            if row:
                chunks.append(" | ".join(str(cell) for cell in row if cell is not None))
    return chunks
