"""Run the isolated JJM embedding comparison benchmark."""
from __future__ import annotations

import argparse
import hashlib
import importlib.metadata
import importlib.util
import json
import platform
import sys
import time
from datetime import datetime, timezone
from pathlib import Path

try:
    import numpy as np
except ImportError:
    np = None

ROOT = Path(__file__).resolve().parents[1]
DATASET = ROOT / "artifacts" / "semantic_benchmark_dataset.json"
OUTPUT = ROOT / "artifacts" / "embedding_benchmark_runtime.json"


def environment() -> dict:
    package_versions = {}
    for name in ["numpy", "torch", "transformers", "FlagEmbedding", "sentence-transformers"]:
        try:
            package_versions[name] = importlib.metadata.version(name)
        except importlib.metadata.PackageNotFoundError:
            package_versions[name] = None
    return {"python": sys.version, "platform": platform.platform(), "machine": platform.machine(), "dataset_sha256": hashlib.sha256(DATASET.read_bytes()).hexdigest(), "package_versions": package_versions}


def blocked(reason: str, models: list[str]) -> int:
    result = {"artifact_type": "embedding_benchmark_runtime", "status": "BLOCKED_BY_MISSING_EMBEDDING_RUNTIME", "timestamp": datetime.now(timezone.utc).isoformat(), "environment": environment(), "models": models, "error": reason, "measurements": []}
    OUTPUT.write_text(json.dumps(result, indent=2), encoding="utf-8")
    print(json.dumps({"status": result["status"], "output": str(OUTPUT), "error": reason}, indent=2))
    return 2


def validate_dataset() -> dict:
    data = json.loads(DATASET.read_text(encoding="utf-8"))
    if not data.get("cases") or not data.get("candidate_units"):
        raise ValueError("Semantic dataset has no cases or candidate units")
    for case in data["cases"]:
        if not case.get("case_id") or not case.get("query") or not case.get("expected_sources"):
            raise ValueError(f"Invalid semantic case: {case}")
    if any(unit.get("unit_type") == "structured_row" for unit in data["candidate_units"]):
        raise ValueError("Raw numeric rows are not allowed in the semantic candidate pool")
    filenames = {unit["filename"] for unit in data["candidate_units"]}
    for case in data["cases"]:
        missing = set(case["expected_sources"]) - filenames
        if missing:
            raise ValueError(f"Expected sources absent for {case['case_id']}: {sorted(missing)}")
    return data


def package_available(name: str) -> bool:
    return importlib.util.find_spec(name) is not None


def load_model(model_key: str, model_path: str, allow_download: bool):
    if not allow_download and not Path(model_path).exists():
        raise RuntimeError(f"Model path is not local: {model_path}; pass --allow-download only in an approved environment")
    if model_key == "bge-m3":
        if not package_available("FlagEmbedding"):
            raise RuntimeError("FlagEmbedding is unavailable")
        from FlagEmbedding import BGEM3FlagModel
        return BGEM3FlagModel(model_path, use_fp16=False)
    if not package_available("sentence_transformers"):
        raise RuntimeError("sentence-transformers is unavailable")
    from sentence_transformers import SentenceTransformer
    return SentenceTransformer(model_path)


def encode(model, model_key: str, texts: list[str], is_query: bool) -> np.ndarray:
    if model_key == "bge-m3":
        return np.asarray(model.encode(texts, return_dense=True, return_sparse=False, return_colbert_vecs=False)["dense_vecs"])
    prefix = "query: " if is_query else "passage: "
    return np.asarray(model.encode([prefix + text for text in texts], normalize_embeddings=True, show_progress_bar=False))


def normalize(vectors: np.ndarray) -> np.ndarray:
    norms = np.linalg.norm(vectors, axis=1, keepdims=True)
    return vectors / np.maximum(norms, 1e-12)


def score_model(model_key: str, model_path: str, revision: str | None, data: dict, allow_download: bool) -> dict:
    load_started = time.perf_counter()
    model = load_model(model_key, model_path, allow_download)
    model_load_seconds = time.perf_counter() - load_started
    units = data["candidate_units"]
    passages = [unit["text"] for unit in units]
    embedding_started = time.perf_counter()
    passage_vectors = normalize(encode(model, model_key, passages, False))
    embedding_seconds = time.perf_counter() - embedding_started
    case_results = []
    reciprocal_ranks = []
    query_latencies = []
    for case in data["cases"]:
        query_started = time.perf_counter()
        query_vector = normalize(encode(model, model_key, [case["query"]], True))[0]
        scores = passage_vectors @ query_vector
        ranked_sources = []
        for index in np.argsort(-scores):
            filename = units[int(index)]["filename"]
            if filename not in ranked_sources:
                ranked_sources.append(filename)
        expected = set(case["expected_sources"])
        first_rank = next((rank + 1 for rank, filename in enumerate(ranked_sources) if filename in expected), None)
        reciprocal_ranks.append(1 / first_rank if first_rank else 0.0)
        query_latencies.append((time.perf_counter() - query_started) * 1000)
        def recall_at(limit: int) -> float:
            return len(set(ranked_sources[:limit]) & expected) / len(expected)
        case_results.append({"case_id": case["case_id"], "expected_sources": sorted(expected), "ranked_sources": ranked_sources[:10], "first_relevant_rank": first_rank, "recall_at_1": recall_at(1), "recall_at_3": recall_at(3), "recall_at_5": recall_at(5), "recall_at_10": recall_at(10)})
    return {"model": model_key, "model_path": model_path, "model_revision": revision, "model_load_seconds": model_load_seconds, "dimensions": int(passage_vectors.shape[1]), "candidate_units": len(passages), "embedding_seconds": embedding_seconds, "throughput_units_per_second": len(passages) / embedding_seconds if embedding_seconds else None, "query_latency_ms": {"mean": sum(query_latencies) / len(query_latencies), "p50": float(np.percentile(query_latencies, 50)), "p95": float(np.percentile(query_latencies, 95))}, "memory_bytes": None, "memory_measurement": "NOT_AVAILABLE_IN_RUNNER", "case_results": case_results, "metrics": {key: sum(item[key] for item in case_results) / len(case_results) for key in ["recall_at_1", "recall_at_3", "recall_at_5", "recall_at_10"]} | {"mrr": sum(reciprocal_ranks) / len(reciprocal_ranks)}}


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--model", choices=["bge-m3", "multilingual-e5-large", "all"], default="all")
    parser.add_argument("--bge-path", default="BAAI/bge-m3")
    parser.add_argument("--e5-path", default="intfloat/multilingual-e5-large")
    parser.add_argument("--revision", default=None)
    parser.add_argument("--allow-download", action="store_true")
    args = parser.parse_args()
    models = [args.model] if args.model != "all" else ["bge-m3", "multilingual-e5-large"]
    if np is None:
        return blocked("NumPy is unavailable in the selected environment", models)
    data = validate_dataset()
    results = []
    errors = []
    for model_key in models:
        try:
            model_path = args.bge_path if model_key == "bge-m3" else args.e5_path
            results.append(score_model(model_key, model_path, args.revision, data, args.allow_download))
        except Exception as exc:
            errors.append({"model": model_key, "error": f"{type(exc).__name__}: {exc}"})
    status = "EXECUTED" if results and not errors else "PARTIAL" if results else "BLOCKED_BY_MISSING_EMBEDDING_RUNTIME"
    output = {"artifact_type": "embedding_benchmark_runtime", "status": status, "timestamp": datetime.now(timezone.utc).isoformat(), "environment": environment(), "dataset": str(DATASET.relative_to(ROOT)), "results": results, "errors": errors, "configuration": vars(args)}
    OUTPUT.write_text(json.dumps(output, indent=2, ensure_ascii=False), encoding="utf-8")
    print(json.dumps({"status": status, "output": str(OUTPUT), "errors": errors}, indent=2))
    return 0 if status == "EXECUTED" else 2


if __name__ == "__main__":
    raise SystemExit(main())
