"""Run an isolated local PostgreSQL + pgvector mechanics benchmark.

Set PGVECTOR_DSN or pass --dsn. The DSN is never printed or persisted. The
benchmark uses canonical semantic units and deterministic diagnostic vectors;
those vectors measure storage/query mechanics, not semantic model quality.
"""
from __future__ import annotations

import argparse
import hashlib
import importlib.metadata
import importlib.util
import math
import json
import os
import platform
import statistics
import sys
import time
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
DATASET = ROOT / "artifacts" / "semantic_benchmark_dataset.json"
OUTPUT = ROOT / "artifacts" / "pgvector_benchmark_runtime.json"
DIMENSIONS = 8


def dataset_sha256() -> str:
    return hashlib.sha256(DATASET.read_bytes()).hexdigest()


def package_versions() -> dict:
    result = {}
    for name in ["psycopg", "pgvector"]:
        try:
            result[name] = importlib.metadata.version(name)
        except importlib.metadata.PackageNotFoundError:
            result[name] = None
    return result


def percentile(values: list[float], fraction: float) -> float | None:
    if not values:
        return None
    ordered = sorted(values)
    index = min(len(ordered) - 1, math.ceil(fraction * len(ordered)) - 1)
    return ordered[index]


def diagnostic_vector(text: str) -> list[float]:
    digest = hashlib.sha256(text.encode("utf-8")).digest()
    return [((byte / 255.0) * 2.0) - 1.0 for byte in digest[:DIMENSIONS]]


def write_result(status: str, **extra) -> int:
    result = {"artifact_type": "pgvector_benchmark_runtime", "status": status, "timestamp": datetime.now(timezone.utc).isoformat(), "environment": {"python": sys.version, "platform": platform.platform(), "package_versions": package_versions(), "postgres_driver_available": importlib.util.find_spec("psycopg") is not None, "pgvector_driver_available": importlib.util.find_spec("pgvector") is not None}, "dataset_sha256": dataset_sha256(), **extra}
    OUTPUT.write_text(json.dumps(result, indent=2, ensure_ascii=False), encoding="utf-8")
    print(json.dumps({"status": status, "output": str(OUTPUT), "error": extra.get("error")}, indent=2))
    return 0 if status == "EXECUTED" else 2


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--dsn", default=os.environ.get("PGVECTOR_DSN"), help="PostgreSQL DSN; prefer PGVECTOR_DSN")
    parser.add_argument("--keep", action="store_true", help="Keep the isolated benchmark schema")
    args = parser.parse_args()
    if not args.dsn:
        return write_result("BLOCKED_BY_MISSING_POSTGRESQL", error="Set PGVECTOR_DSN or pass --dsn; no DSN was supplied.")
    if importlib.util.find_spec("psycopg") is None or importlib.util.find_spec("pgvector") is None:
        return write_result("BLOCKED_BY_MISSING_PGVECTOR_RUNTIME", error="psycopg and pgvector packages are required in the isolated environment.")
    import psycopg
    from pgvector.psycopg import register_vector
    data = json.loads(DATASET.read_text(encoding="utf-8"))
    units = data.get("candidate_units", [])[:100]
    if not units:
        return write_result("BLOCKED_BY_INVALID_DATASET", error="No candidate semantic units are available.")
    if any(unit.get("filename") == "Status of Pipe Water Supply in School (2).xls" for unit in units):
        return write_result("BLOCKED_BY_INVALID_DATASET", error="Excluded corrupted source appears in the semantic dataset.")
    schema = "phase5b_" + datetime.now(timezone.utc).strftime("%Y%m%d%H%M%S")
    insert_seconds = []
    query_seconds = []
    conn = None
    try:
        conn = psycopg.connect(args.dsn)
        register_vector(conn)
        with conn.cursor() as cursor:
            cursor.execute("CREATE EXTENSION IF NOT EXISTS vector")
            cursor.execute(f"CREATE SCHEMA {schema}")
            cursor.execute(f"CREATE TABLE {schema}.units (id integer PRIMARY KEY, embedding vector({DIMENSIONS}), filename text NOT NULL, state text, district text, report_family text, report_date text, sha256 text, content text NOT NULL)")
            for index, unit in enumerate(units):
                started = time.perf_counter()
                cursor.execute(f"INSERT INTO {schema}.units VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s)", (index, diagnostic_vector(unit["text"]), unit["filename"], unit.get("provenance", {}).get("state"), unit.get("provenance", {}).get("district"), unit.get("provenance", {}).get("format_code"), unit.get("provenance", {}).get("date"), unit.get("provenance", {}).get("sha256"), unit["text"]))
                insert_seconds.append(time.perf_counter() - started)
            started = time.perf_counter()
            cursor.execute(f"CREATE INDEX {schema}_hnsw ON {schema}.units USING hnsw (embedding vector_cosine_ops)")
            index_seconds = time.perf_counter() - started
            cursor.execute(f"CREATE INDEX {schema}_filename ON {schema}.units (filename)")
            cursor.execute(f"CREATE INDEX {schema}_metadata ON {schema}.units (state, district, report_family, report_date)")
            conn.commit()
            query_vector = diagnostic_vector(units[0]["text"])
            for _ in range(20):
                started = time.perf_counter()
                cursor.execute(f"SELECT id, filename, sha256 FROM {schema}.units ORDER BY embedding <=> %s::vector LIMIT 10", (query_vector,))
                cursor.fetchall()
                query_seconds.append((time.perf_counter() - started) * 1000)
            cursor.execute(f"SELECT count(*) FROM {schema}.units WHERE filename = %s", (units[0]["filename"],))
            exact_count = cursor.fetchone()[0]
            cursor.execute(f"SELECT count(*) FROM {schema}.units WHERE state IS NULL OR state = %s", (units[0].get("provenance", {}).get("state"),))
            filtered_count = cursor.fetchone()[0]
            cursor.execute(f"SELECT id, filename, sha256 FROM {schema}.units WHERE id = %s", (0,))
            provenance_row = cursor.fetchone()
            conn.commit()
        return write_result("EXECUTED", environment={"python": sys.version, "platform": platform.platform()}, schema=schema, vector_source="DETERMINISTIC_TEST_VECTOR_NOT_SEMANTIC", unit_count=len(units), insertion_throughput_units_per_second=len(units) / sum(insert_seconds) if sum(insert_seconds) else None, index_build_seconds=index_seconds, query_latency_ms={"p50": statistics.median(query_seconds), "p95": sorted(query_seconds)[max(0, int(len(query_seconds) * 0.95) - 1)], "p99": sorted(query_seconds)[max(0, int(len(query_seconds) * 0.99) - 1)]}, correctness={"exact_lookup_rows": exact_count, "filtered_rows": filtered_count, "provenance_retrieved": provenance_row is not None, "semantic_top_k_quality":"NOT_EVALUABLE_WITH_DIAGNOSTIC_VECTORS"}, storage_bytes=None, configuration={"unit_limit":100,"dimensions":DIMENSIONS})
    except Exception as exc:
        return write_result("BLOCKED_BY_PGVECTOR_EXECUTION_ERROR", error=f"{type(exc).__name__}: {exc}", schema=schema)
    finally:
        if conn is not None:
            if not args.keep:
                try:
                    with conn.cursor() as cursor:
                        cursor.execute(f"DROP SCHEMA IF EXISTS {schema} CASCADE")
                        conn.commit()
                except Exception:
                    conn.rollback()
            conn.close()


if __name__ == "__main__":
    raise SystemExit(main())
