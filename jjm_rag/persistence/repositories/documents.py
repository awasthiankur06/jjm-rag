from __future__ import annotations

import sqlite3
from typing import Any


class DocumentRepository:
    def __init__(self, conn: sqlite3.Connection):
        self.conn = conn

    def create(self, document: dict[str, Any]) -> dict[str, Any]:
        self.conn.execute(
            """
            INSERT OR IGNORE INTO documents (
                document_id, filename, extracted_document_title, title_provenance, title_confidence,
                original_path, sha256, source_format, family,
                report_type, report_title, format_code, ingestion_status, quality_state,
                production_included, ingested_at
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, CURRENT_TIMESTAMP)
            """,
            (
                document["document_id"],
                document.get("filename"),
                document.get("extracted_document_title"),
                document.get("title_provenance"),
                document.get("title_confidence"),
                document.get("original_path"),
                document.get("sha256"),
                document.get("source_format"),
                document.get("family"),
                document.get("report_type"),
                document.get("report_title"),
                document.get("format_code"),
                document.get("ingestion_status", "PENDING"),
                document.get("quality_state"),
                bool(document.get("production_included", False)),
            ),
        )
        self.conn.commit()
        return self.get_by_id(document["document_id"])

    def get_by_id(self, document_id: str) -> dict[str, Any] | None:
        row = self.conn.execute(
            "SELECT * FROM documents WHERE document_id = ?",
            (document_id,),
        ).fetchone()
        return dict(row) if row else None

    def get_by_sha256(self, sha256: str) -> dict[str, Any] | None:
        row = self.conn.execute(
            "SELECT * FROM documents WHERE sha256 = ?",
            (sha256,),
        ).fetchone()
        return dict(row) if row else None

    def list(self, filters: dict[str, Any] | None = None, limit: int | None = None) -> list[dict[str, Any]]:
        query = "SELECT * FROM documents WHERE 1 = 1"
        params: list[Any] = []
        if filters:
            for key, value in filters.items():
                query += f" AND {key} = ?"
                params.append(value)
        if limit is not None:
            query += " LIMIT ?"
            params.append(limit)
        rows = self.conn.execute(query, tuple(params)).fetchall()
        return [dict(row) for row in rows]

    def update_ingestion_status(self, document_id: str, ingestion_status: str, quality_state: str | None = None) -> None:
        query = "UPDATE documents SET ingestion_status = ?, quality_state = COALESCE(?, quality_state) WHERE document_id = ?"
        self.conn.execute(query, (ingestion_status, quality_state, document_id))
        self.conn.commit()

    def count(self, filters: dict[str, Any] | None = None) -> int:
        query = "SELECT COUNT(*) FROM documents WHERE 1 = 1"
        params: list[Any] = []
        if filters:
            for key, value in filters.items():
                query += f" AND {key} = ?"
                params.append(value)
        row = self.conn.execute(query, tuple(params)).fetchone()
        return int(row["count"] if isinstance(row, dict) else row[0])
