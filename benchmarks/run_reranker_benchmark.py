"""Compare the validated no-reranker baseline with an optional local cross-encoder."""
from __future__ import annotations

import argparse
import hashlib
import importlib.metadata
import importlib.util
import json
import platform
import sys
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
POST = ROOT / "artifacts" / "retrieval_evaluation_post_remediation.json"
OUTPUT = ROOT / "artifacts" / "reranker_benchmark_runtime.json"


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--model-path", default=None)
    args = parser.parse_args()
    post = json.loads(POST.read_text(encoding="utf-8"))
    baseline = {key: post["metrics"].get(key) for key in ["recall_at_1", "recall_at_3", "recall_at_5", "recall_at_10"]}
    if importlib.util.find_spec("sentence_transformers") is None or not args.model_path:
        result = {"artifact_type":"reranker_benchmark_runtime","status":"BLOCKED_BY_MISSING_RERANKER_RUNTIME","timestamp":datetime.now(timezone.utc).isoformat(),"environment":{"python":sys.version,"platform":platform.platform(),"package_versions":{"sentence-transformers":importlib.metadata.version("sentence-transformers") if importlib.util.find_spec("sentence_transformers") else None},"sentence_transformers_available":importlib.util.find_spec("sentence_transformers") is not None},"dataset_sha256":hashlib.sha256(POST.read_bytes()).hexdigest(),"baseline":{"name":"validated hybrid retrieval without reranker","metrics":baseline},"candidate":{"status":"NOT_RUN","reason":"Install an approved sentence-transformers runtime and pass a local --model-path; no automatic download is performed."},"decision":"NOT_JUSTIFIED"}
        OUTPUT.write_text(json.dumps(result, indent=2), encoding="utf-8")
        print(json.dumps({"status":result["status"],"output":str(OUTPUT)}, indent=2))
        return 2
    from sentence_transformers import CrossEncoder
    reranker = CrossEncoder(args.model_path)
    result = {"artifact_type":"reranker_benchmark_runtime","status":"NOT_IMPLEMENTED_FOR_PRODUCTION_DATA","timestamp":datetime.now(timezone.utc).isoformat(),"environment":{"python":sys.version,"platform":platform.platform()},"dataset_sha256":hashlib.sha256(POST.read_bytes()).hexdigest(),"baseline":{"metrics":baseline},"candidate":{"model_path":args.model_path,"loaded":True,"note":"Candidate loaded; case-level candidate generation and answer-level reranker evaluation must be wired in an approved isolated experiment."},"decision":"REQUIRES_BENCHMARK"}
    OUTPUT.write_text(json.dumps(result, indent=2), encoding="utf-8")
    print(json.dumps({"status":result["status"],"output":str(OUTPUT)}, indent=2))
    return 2


if __name__ == "__main__":
    raise SystemExit(main())
