from __future__ import annotations

import json
import sqlite3
from typing import Any


class GeographyRepository:
    def __init__(self, conn):
        self.conn = conn

    def upsert(self, geography: dict[str, Any]) -> dict[str, Any]:
        self.conn.execute(
            """
            INSERT OR REPLACE INTO geography_dimensions (
                geography_id, document_id, state_name, district_name, division_name,
                block_name, habitation_name, raw_label
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            """,
            tuple(geography.get(key) for key in (
                "geography_id", "document_id", "state_name", "district_name",
                "division_name", "block_name", "habitation_name", "raw_label",
            )),
        )
        self.conn.commit()
        return self.get_by_id(geography["geography_id"])

    def get_by_id(self, geography_id: str) -> dict[str, Any] | None:
        row = self.conn.execute("SELECT * FROM geography_dimensions WHERE geography_id = ?", (geography_id,)).fetchone()
        return dict(row) if row else None

    def count(self) -> int:
        row = self.conn.execute("SELECT COUNT(*) AS count FROM geography_dimensions").fetchone()
        return int(row["count"] if isinstance(row, dict) else row[0])


class ReportingRepository:
    def __init__(self, conn):
        self.conn = conn

    def upsert(self, reporting: dict[str, Any]) -> dict[str, Any]:
        self.conn.execute(
            """
            INSERT OR REPLACE INTO reporting_dimensions (
                reporting_id, document_id, report_date, reporting_period,
                financial_year, snapshot_label, metric_name, format_code, report_family
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            tuple(reporting.get(key) for key in (
                "reporting_id", "document_id", "report_date", "reporting_period",
                "financial_year", "snapshot_label", "metric_name", "format_code", "report_family",
            )),
        )
        self.conn.commit()
        return self.get_by_id(reporting["reporting_id"])

    def get_by_id(self, reporting_id: str) -> dict[str, Any] | None:
        row = self.conn.execute("SELECT * FROM reporting_dimensions WHERE reporting_id = ?", (reporting_id,)).fetchone()
        return dict(row) if row else None

    def count(self) -> int:
        row = self.conn.execute("SELECT COUNT(*) AS count FROM reporting_dimensions").fetchone()
        return int(row["count"] if isinstance(row, dict) else row[0])


class IngestionAuditRepository:
    def __init__(self, conn):
        self.conn = conn

    def create(self, audit: dict[str, Any]) -> dict[str, Any]:
        details = audit.get("details")
        if (isinstance(self.conn, sqlite3.Connection) or getattr(self.conn, "is_sqlite", False)) and isinstance(details, (dict, list)):
            details = json.dumps(details)
        self.conn.execute(
            """
            INSERT OR REPLACE INTO ingestion_audit (
                audit_id, document_id, source_filename, source_sha256, status, reason, details
            ) VALUES (?, ?, ?, ?, ?, ?, ?)
            """,
            tuple(audit.get(key) for key in (
                "audit_id", "document_id", "source_filename", "source_sha256",
                "status", "reason",
            )) + (details,),
        )
        self.conn.commit()
        return self.get_by_id(audit["audit_id"])

    def get_by_id(self, audit_id: str) -> dict[str, Any] | None:
        row = self.conn.execute("SELECT * FROM ingestion_audit WHERE audit_id = ?", (audit_id,)).fetchone()
        return dict(row) if row else None

    def count(self) -> int:
        row = self.conn.execute("SELECT COUNT(*) AS count FROM ingestion_audit").fetchone()
        return int(row["count"] if isinstance(row, dict) else row[0])
