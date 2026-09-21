from __future__ import annotations

import sqlite3
from typing import Any


class ProvenanceRepository:
    def __init__(self, conn: sqlite3.Connection):
        self.conn = conn

    def create(self, provenance: dict[str, Any]) -> dict[str, Any]:
        self.conn.execute(
            """
            INSERT OR REPLACE INTO provenance_records (
                provenance_id, document_id, page_number, sheet_name, table_name,
                section_name, row_index, column_index, cell_reference,
                source_row_index, source_col_index, origin_cell_id
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                provenance["provenance_id"],
                provenance["document_id"],
                provenance.get("page_number"),
                provenance.get("sheet_name"),
                provenance.get("table_name"),
                provenance.get("section_name"),
                provenance.get("row_index"),
                provenance.get("column_index"),
                provenance.get("cell_reference"),
                provenance.get("source_row_index"),
                provenance.get("source_col_index"),
                provenance.get("origin_cell_id"),
            ),
        )
        self.conn.commit()
        return self.get_by_id(provenance["provenance_id"])

    def get_by_id(self, provenance_id: str) -> dict[str, Any] | None:
        row = self.conn.execute(
            "SELECT * FROM provenance_records WHERE provenance_id = ?",
            (provenance_id,),
        ).fetchone()
        return dict(row) if row else None

    def list_for_document(self, document_id: str) -> list[dict[str, Any]]:
        rows = self.conn.execute(
            "SELECT * FROM provenance_records WHERE document_id = ? ORDER BY created_at ASC",
            (document_id,),
        ).fetchall()
        return [dict(row) for row in rows]
