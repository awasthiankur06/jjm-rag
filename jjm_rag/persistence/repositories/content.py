from __future__ import annotations

import sqlite3
from typing import Any


class CanonicalContentRepository:
    def __init__(self, conn: sqlite3.Connection):
        self.conn = conn

    def insert(self, content: dict[str, Any]) -> dict[str, Any]:
        self.conn.execute(
            """
            INSERT OR REPLACE INTO canonical_content (
                content_id, document_id, parent_content_id, content_type,
                section_name, row_identity, canonical_text, source_text,
                provenance_id
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                content["content_id"],
                content["document_id"],
                content.get("parent_content_id"),
                content.get("content_type", "text"),
                content.get("section_name"),
                content.get("row_identity"),
                content.get("canonical_text"),
                content.get("source_text"),
                content.get("provenance_id"),
            ),
        )
        self.conn.commit()
        return self.get_by_id(content["content_id"])

    def get_by_id(self, content_id: str) -> dict[str, Any] | None:
        row = self.conn.execute(
            "SELECT * FROM canonical_content WHERE content_id = ?",
            (content_id,),
        ).fetchone()
        return dict(row) if row else None

    def list_by_document(self, document_id: str) -> list[dict[str, Any]]:
        rows = self.conn.execute(
            "SELECT * FROM canonical_content WHERE document_id = ? ORDER BY created_at ASC",
            (document_id,),
        ).fetchall()
        return [dict(row) for row in rows]
