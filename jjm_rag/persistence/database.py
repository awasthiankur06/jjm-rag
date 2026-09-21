from __future__ import annotations

import os
import re
import sqlite3
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Iterator, Protocol
from contextlib import contextmanager


class DatabaseSession(Protocol):
    def execute(self, query: str, params: tuple[Any, ...] | list[Any] | None = None):
        ...

    def executemany(self, query: str, params):
        ...

    def commit(self):
        ...

    def rollback(self):
        ...

    def close(self):
        ...


class PostgresConnection:
    _conflict_keys = {
        "document_versions": "version_id",
        "provenance_records": "provenance_id",
        "structured_records": "record_id",
        "observations": "observation_id",
        "canonical_content": "content_id",
        "geography_dimensions": "geography_id",
        "reporting_dimensions": "reporting_id",
        "ingestion_audit": "audit_id",
    }

    def __init__(self, connection):
        self.connection = connection

    def execute(self, query: str, params: tuple[Any, ...] | list[Any] | None = None):
        import psycopg
        from psycopg.types.json import Jsonb

        normalized = query.replace("?", "%s")
        document_insert = "INSERT OR IGNORE INTO documents" in normalized
        replace_match = re.search(r"INSERT OR REPLACE INTO (\w+)", normalized)
        if document_insert:
            normalized = normalized.replace("INSERT OR IGNORE INTO documents", "INSERT INTO documents")
            normalized = normalized.rstrip() + " ON CONFLICT (document_id) DO NOTHING"
        elif replace_match:
            table = replace_match.group(1)
            key = self._conflict_keys[table]
            normalized = normalized.replace(f"INSERT OR REPLACE INTO {table}", f"INSERT INTO {table}")
            normalized = normalized.rstrip() + f" ON CONFLICT ({key}) DO NOTHING"
        adapted_params = tuple(Jsonb(value) if isinstance(value, (dict, list)) else value for value in (params or ()))
        return self.connection.execute(normalized, adapted_params)

    def executemany(self, query: str, params):
        normalized = query.replace("?", "%s")
        return self.connection.executemany(normalized, params)

    def commit(self):
        return self.connection.commit()

    def rollback(self):
        return self.connection.rollback()

    def close(self):
        return self.connection.close()


class TransactionSession:
    """Suppress repository-level commits until one logical ingestion completes."""

    def __init__(self, connection: DatabaseSession):
        self.connection = connection
        self.is_sqlite = isinstance(connection, sqlite3.Connection)

    def execute(self, query: str, params: tuple[Any, ...] | list[Any] | None = None):
        return self.connection.execute(query, params)

    def executemany(self, query: str, params):
        return self.connection.executemany(query, params)

    def commit(self):
        # Repositories remain usable independently, but cannot commit a partial
        # source while this transaction wrapper is active.
        return None

    def rollback(self):
        return None


@contextmanager
def transaction(connection: DatabaseSession) -> Iterator[TransactionSession]:
    """Commit all writes for a source together, or roll them all back."""
    session = TransactionSession(connection)
    try:
        # SQLite needs an explicit transaction; PostgreSQL accepts BEGIN as well.
        connection.execute("BEGIN")
        yield session
        connection.commit()
    except Exception:
        connection.rollback()
        raise


@dataclass
class DatabaseConfig:
    dsn: str | None = None
    sqlite_path: str | None = None
    postgres_available: bool = False

    @property
    def effective_dsn(self) -> str:
        return self.dsn or self.sqlite_path or ":memory:"


def sqlite_connection(path: str | None = None) -> sqlite3.Connection:
    database_path = path or os.getenv("JJM_SQLITE_PATH") or ":memory:"
    if database_path != ":memory:":
        Path(database_path).parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(database_path)
    # SQLite disables FK enforcement by default; enable it so unit tests do not
    # mask integrity failures that PostgreSQL would reject.
    conn.execute("PRAGMA foreign_keys = ON")
    conn.row_factory = sqlite3.Row
    return conn


def apply_migration(conn: DatabaseSession, migration_path: str | Path) -> None:
    migration = Path(migration_path).read_text(encoding="utf-8")
    if isinstance(conn, sqlite3.Connection):
        conn.executescript(migration)
    else:
        conn.execute(migration)
    conn.commit()


def get_database_session() -> DatabaseSession:
    dsn = os.getenv("JJM_DATABASE_URL")
    if dsn:
        try:
            import psycopg

            from psycopg.rows import dict_row

            conn = psycopg.connect(dsn, row_factory=dict_row)
            return PostgresConnection(conn)
        except Exception as error:
            # An explicitly requested PostgreSQL backend must not silently turn
            # into SQLite; callers need an actionable persistence failure.
            raise RuntimeError("Unable to connect to configured PostgreSQL database") from error
    return sqlite_connection(os.getenv("JJM_SQLITE_PATH", ":memory:"))


def get_database_config() -> DatabaseConfig:
    dsn = os.getenv("JJM_DATABASE_URL")
    sqlite_path = os.getenv("JJM_SQLITE_PATH")
    postgres_available = bool(dsn)
    return DatabaseConfig(dsn=dsn, sqlite_path=sqlite_path, postgres_available=postgres_available)
