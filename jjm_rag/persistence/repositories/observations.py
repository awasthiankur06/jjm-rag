from __future__ import annotations

import sqlite3
from typing import Any


class ObservationRepository:
    def __init__(self, conn: sqlite3.Connection):
        self.conn = conn

    def insert(self, observation: dict[str, Any]) -> dict[str, Any]:
        self.conn.execute(
            """
            INSERT OR REPLACE INTO observations (
                observation_id, document_id, record_id, metric_name, value_raw,
                value_numeric, unit, normalization_status, provenance_id, header_path
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                observation["observation_id"],
                observation["document_id"],
                observation.get("record_id"),
                observation.get("metric_name"),
                observation.get("value_raw"),
                observation.get("value_numeric"),
                observation.get("unit"),
                observation.get("normalization_status", "RAW"),
                observation.get("provenance_id"),
                observation.get("header_path"),
            ),
        )
        self.conn.commit()
        return self.get_by_id(observation["observation_id"])

    def get_by_id(self, observation_id: str) -> dict[str, Any] | None:
        row = self.conn.execute(
            "SELECT * FROM observations WHERE observation_id = ?",
            (observation_id,),
        ).fetchone()
        return dict(row) if row else None

    def filter(self, filters: dict[str, Any] | None = None, limit: int | None = None) -> list[dict[str, Any]]:
        query = "SELECT * FROM observations WHERE 1 = 1"
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
