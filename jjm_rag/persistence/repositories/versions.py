from __future__ import annotations

import sqlite3
import json
from typing import Any


class VersionRepository:
    def __init__(self, conn: sqlite3.Connection):
        self.conn = conn

    def create(self, version: dict[str, Any]) -> dict[str, Any]:
        snapshot_metadata = version.get("snapshot_metadata")
        if (isinstance(self.conn, sqlite3.Connection) or getattr(self.conn, "is_sqlite", False)) and isinstance(snapshot_metadata, (dict, list)):
            snapshot_metadata = json.dumps(snapshot_metadata)
        self.conn.execute(
            """
            INSERT OR REPLACE INTO document_versions (
                version_id, document_id, content_hash, structural_fingerprint, content_signature,
                version_evidence, version_confidence, snapshot_metadata
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                version["version_id"],
                version["document_id"],
                version.get("content_hash"),
                version.get("structural_fingerprint"),
                version.get("content_signature"),
                version.get("version_evidence", "INSUFFICIENT_VERSION_EVIDENCE"),
                version.get("version_confidence", "UNKNOWN"),
                snapshot_metadata,
            ),
        )
        self.conn.commit()
        return self.list_for_document(version["document_id"])

    def list_for_document(self, document_id: str) -> list[dict[str, Any]]:
        rows = self.conn.execute(
            "SELECT * FROM document_versions WHERE document_id = ? ORDER BY created_at DESC",
            (document_id,),
        ).fetchall()
        return [dict(row) for row in rows]

    def list_snapshots_for_family(self, family: str) -> list[dict[str, Any]]:
        rows = self.conn.execute(
            "SELECT v.* FROM document_versions v JOIN documents d ON d.document_id = v.document_id WHERE d.family = ? ORDER BY v.created_at DESC",
            (family,),
        ).fetchall()
        return [dict(row) for row in rows]
