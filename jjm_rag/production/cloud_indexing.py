from __future__ import annotations

import json
import os
import sys
import time
from collections import deque
from collections import Counter
from datetime import datetime, timezone
import uuid
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from jjm_rag.semantic.contracts import SemanticDocument

from .qdrant import QdrantCloudStore
from .gemini import GeminiRateLimitError
from .providers import ProviderError
from jjm_rag.semantic.candidates import select_semantic_candidates


@dataclass
class IndexRun:
    status: str
    candidate_count: int
    embedded_count: int = 0
    upserted_count: int = 0
    failed_count: int = 0
    skipped_count: int = 0
    errors: list[str] | None = None
    gemini_requests: int = 0
    successful_batches: int = 0
    rate_limit_retries: int = 0
    provider_failures: int = 0
    qdrant_points: int = 0


def load_candidates(path: str | Path) -> list[dict[str, Any]]:
    data = json.loads(Path(path).read_text(encoding="utf-8"))
    candidates = data.get("candidates", [])
    if data.get("eligible_candidate_count") != len(candidates):
        raise ValueError("candidate manifest declared count does not match its candidates")
    if any(item.get("filename") == "Status of Pipe Water Supply in School (2).xls" for item in candidates):
        raise ValueError("excluded source is present in semantic candidates")
    return candidates


def build_candidate_manifest(conn: Any, destination: str | Path) -> dict[str, Any]:
    """Materialize semantic candidates from the current canonical database.

    The semantic index is derived data.  Rebuilding canonical content changes
    stable content identities when source structure is corrected, so an old
    candidate artifact must never be treated as authoritative.
    """
    rows = conn.execute(
        """
        SELECT c.content_id, c.document_id, c.parent_content_id, c.content_type,
               c.section_name, c.row_identity, c.canonical_text, d.filename,
               d.family, d.report_type, d.production_included,
               p.page_number, p.sheet_name, p.table_name, p.section_name AS provenance_section,
               p.row_index, p.column_index, p.cell_reference
        FROM canonical_content c
        JOIN documents d ON d.document_id = c.document_id
        LEFT JOIN provenance_records p ON p.provenance_id = c.provenance_id
        WHERE d.production_included = TRUE
        ORDER BY d.filename, c.content_id
        """
    ).fetchall()
    source_rows = [dict(row) for row in rows]
    for row in source_rows:
        row["provenance"] = {
            key: row.pop(key)
            for key in ("page_number", "sheet_name", "table_name", "provenance_section", "row_index", "column_index", "cell_reference")
            if row.get(key) is not None
        }
        row["geography"] = {}
        row["reporting"] = {}

    candidates, decisions = select_semantic_candidates(source_rows)
    reason_counts = Counter(decision.reason for decision in decisions if not decision.eligible)
    result = {
        "artifact_type": "semantic_candidate_manifest",
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "source": "current PostgreSQL canonical_content joined to documents and provenance_records",
        "canonical_source_of_truth": True,
        "total_canonical_content_units_observed": len(source_rows),
        "eligible_candidate_count": len(candidates),
        "excluded_unit_count": len(source_rows) - len(candidates),
        "exclusion_reasons": dict(sorted(reason_counts.items())),
        "excluded_source_candidate_count": sum(
            candidate.get("filename") == "Status of Pipe Water Supply in School (2).xls"
            for candidate in candidates
        ),
        "candidates": candidates,
    }
    if result["excluded_source_candidate_count"]:
        raise ValueError("excluded source is present in regenerated semantic candidates")
    Path(destination).write_text(json.dumps(result, indent=2, ensure_ascii=False), encoding="utf-8")
    return result


def candidate_to_semantic_document(candidate: dict[str, Any], model: str = "gemini-embedding-001", dimension: int = 768, provider: str = "google-gemini") -> SemanticDocument:
    return SemanticDocument(
        content_id=candidate["content_id"],
        document_id=candidate["document_id"],
        version_id=candidate.get("version_id"),
        text=candidate["canonical_text"],
        content_hash=candidate["content_hash"],
        source_filename=candidate["filename"],
        source_family=candidate.get("family"),
        report_type=candidate.get("report_type"),
        geography=candidate.get("geography", {}),
        reporting=candidate.get("reporting", {}),
        provenance=candidate.get("provenance", {}),
        model_name=model,
        embedding_provider=provider,
        embedding_dimension=dimension,
    )


def dry_run(manifest_path: str | Path, limit: int | None = None) -> IndexRun:
    candidates = load_candidates(manifest_path)
    selected = candidates[:limit] if limit else candidates
    return IndexRun("DRY_RUN", len(selected), skipped_count=len(candidates) - len(selected), errors=[])


def index_candidates(manifest_path: str | Path, *, limit: int | None = None, provider: Any | None = None, store: QdrantCloudStore | None = None, checkpoint_path: str | Path | None = None, max_new: int | None = None) -> IndexRun:
    candidates = load_candidates(manifest_path)
    selected = candidates[:limit] if limit else candidates
    if provider is None:
        from .gemini import GeminiEmbeddingProvider
        provider = GeminiEmbeddingProvider()
    store = store or QdrantCloudStore()
    store.ensure_collection(provider.dimension)
    existing_points = store._get_client().scroll(collection_name=store.collection, limit=10000, with_payload=True, with_vectors=True)[0]
    existing_ids = {(point.payload or {}).get("content_unit_id") for point in existing_points}
    manifest_ids = {candidate["content_id"] for candidate in selected}
    _validate_existing_points(existing_points, manifest_ids, provider)
    successful_ids: list[str] = []
    checkpoint: dict[str, Any] = {}
    if checkpoint_path and Path(checkpoint_path).exists():
        try:
            checkpoint = json.loads(Path(checkpoint_path).read_text(encoding="utf-8"))
            successful_ids = list(checkpoint.get("successful_content_ids", []))
        except (OSError, json.JSONDecodeError):
            successful_ids = []
    successful_ids = sorted(set(successful_ids) | existing_ids)
    if checkpoint_path:
        checkpoint.update({"successful_content_ids": successful_ids, "candidate_count": len(selected), "indexed_count": len(existing_ids), "remaining_count": len(manifest_ids - existing_ids), "complete": len(existing_ids) == len(selected)})
        Path(checkpoint_path).write_text(json.dumps(checkpoint, indent=2), encoding="utf-8")
    records = [candidate_to_semantic_document(candidate, model=provider.model_name, dimension=provider.dimension, provider="google-gemini") for candidate in selected if candidate["content_id"] not in existing_ids]
    if max_new is not None:
        records = records[:max_new]
    embedded = 0
    upserted = 0
    errors: list[str] = []
    batch_size = min(provider.config.batch_size, int(os.getenv("GEMINI_INDEX_BATCH_SIZE", "8")))
    requests = 0
    successful_batches = 0
    rate_limit_retries = 0
    provider_failures = 0
    token_window: deque[tuple[float, int]] = deque()
    safe_tpm = int(provider.config.tpm_quota * provider.config.tpm_safety_fraction)
    for start in range(0, len(records), batch_size):
        batch = records[start:start + batch_size]
        try:
            estimated_tokens = sum(provider.estimate_tokens(record.text) for record in batch)
            while True:
                now = time.monotonic()
                while token_window and now - token_window[0][0] >= provider.config.rolling_window_seconds:
                    token_window.popleft()
                used_tokens = sum(tokens for _, tokens in token_window)
                if used_tokens + estimated_tokens <= safe_tpm:
                    break
                wait_seconds = max(0.25, provider.config.rolling_window_seconds - (now - token_window[0][0]))
                print(f"TPM gate: waiting {wait_seconds:.1f}s; estimated={estimated_tokens}; rolling={used_tokens}; safe_budget={safe_tpm}", file=sys.stderr, flush=True)
                time.sleep(wait_seconds)
            if token_window and provider.config.request_delay_seconds:
                time.sleep(provider.config.request_delay_seconds)
            requests += 1
            vectors = provider.embed_documents([record.text for record in batch])
            if len(vectors) != len(batch) or any(len(vector) != provider.dimension for vector in vectors):
                raise ProviderError("embedding batch failed dimension validation")
            embedded += len(vectors)
            upserted += store.upsert(batch, vectors)
            observed_tokens = getattr(provider, "last_request_stats", None)
            token_window.append((time.monotonic(), int(getattr(observed_tokens, "observed_tokens", None) or estimated_tokens)))
            successful_batches += 1
            successful_ids.extend(record.content_id for record in batch)
            if checkpoint_path:
                Path(checkpoint_path).write_text(json.dumps({"embedded": embedded, "upserted": upserted, "last_batch_start": start, "successful_content_ids": sorted(set(successful_ids)), "candidate_count": len(selected), "complete": len(existing_ids | set(successful_ids)) >= len(selected)}, indent=2), encoding="utf-8")
            print(f"Indexed: {len(existing_ids) + len(successful_ids)} / {len(selected)}\nRemaining: {max(0, len(selected) - len(existing_ids) - len(successful_ids))}\nCurrent batch: {start}:{start + len(batch)}\nGemini requests: {requests}\nSuccessful batches: {successful_batches}\nRate-limit retries: {rate_limit_retries}\nProvider failures: {provider_failures}\nQdrant points: {len(existing_points) + upserted}", file=sys.stderr, flush=True)
        except GeminiRateLimitError as error:
            rate_limit_retries += error.retries
            provider_failures += 1
            errors.append(f"batch {start}:{start + len(batch)}: RATE_LIMITED: {error}; retry_after={error.retry_after}")
            break
        except Exception as error:
            provider_failures += 1
            errors.append(f"batch {start}:{start + len(batch)}: {type(error).__name__}: {error}")
            break
    return IndexRun("SUCCESS" if not errors else "FAILED", len(selected), embedded, upserted, 0 if not errors else len(records) - embedded, len(candidates) - len(selected), errors, requests, successful_batches, rate_limit_retries, provider_failures, len(existing_points) + upserted)


def _validate_existing_points(points: list[Any], candidate_ids: set[str], provider: Any) -> None:
    seen: set[str] = set()
    for point in points:
        payload = point.payload or {}
        content_id = payload.get("content_unit_id")
        if not content_id or content_id in seen:
            raise ProviderError("existing Qdrant points contain duplicate or missing canonical IDs")
        if content_id not in candidate_ids:
            raise ProviderError("existing Qdrant point is outside the approved semantic candidate set")
        if point.id != QdrantCloudStore.point_id(content_id):
            raise ProviderError("existing Qdrant point has a non-deterministic point ID")
        if payload.get("embedding_model") != provider.model_name or payload.get("embedding_provider") != "google-gemini" or payload.get("embedding_dimension") != provider.dimension:
            raise ProviderError("existing Qdrant point has incompatible embedding metadata")
        vector = getattr(point, "vector", None)
        if vector is not None and len(vector) != provider.dimension:
            raise ProviderError("existing Qdrant point has an incompatible vector dimension")
        if payload.get("filename") == "Status of Pipe Water Supply in School (2).xls":
            raise ProviderError("excluded source is present in Qdrant semantic collection")
        seen.add(content_id)
