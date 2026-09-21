from __future__ import annotations

import sqlite3
from typing import Any


class StructuredRecordRepository:
    def __init__(self, conn: sqlite3.Connection):
        self.conn = conn

    def insert(self, record: dict[str, Any]) -> dict[str, Any]:
        self.conn.execute(
            """
            INSERT OR REPLACE INTO structured_records (
                record_id, document_id, table_name, row_identity, column_identity,
                metric_name, value_raw, value_numeric, unit, geography_id,
                reporting_id, provenance_id, header_path
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                record["record_id"],
                record["document_id"],
                record.get("table_name"),
                record.get("row_identity"),
                record.get("column_identity"),
                record.get("metric_name"),
                record.get("value_raw"),
                record.get("value_numeric"),
                record.get("unit"),
                record.get("geography_id"),
                record.get("reporting_id"),
                record.get("provenance_id"),
                record.get("header_path"),
            ),
        )
        self.conn.commit()
        return self.get_by_id(record["record_id"])

    def get_by_id(self, record_id: str) -> dict[str, Any] | None:
        row = self.conn.execute(
            "SELECT * FROM structured_records WHERE record_id = ?",
            (record_id,),
        ).fetchone()
        return dict(row) if row else None

    def list_by_document(self, document_id: str) -> list[dict[str, Any]]:
        rows = self.conn.execute(
            "SELECT * FROM structured_records WHERE document_id = ? ORDER BY created_at ASC",
            (document_id,),
        ).fetchall()
        return [dict(row) for row in rows]

    def filter(self, filters: dict[str, Any] | None = None, limit: int | None = None) -> list[dict[str, Any]]:
        query = "SELECT * FROM structured_records WHERE 1 = 1"
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
