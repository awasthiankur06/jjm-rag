"""Single entry point for Phase 5B isolated benchmark tooling."""
from __future__ import annotations

import json
import hashlib
import platform
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
OUTPUT = ROOT / "artifacts" / "phase5b_run_all.json"
COMMANDS = {
    "embedding": ["run_embedding_benchmark.py"],
    "pgvector": ["run_pgvector_benchmark.py"],
    "grok": ["run_grok_benchmark.py"],
    "reranker": ["run_reranker_benchmark.py"],
}
FRAMEWORKS = [
    ROOT / "benchmarks/framework_bakeoff/custom_python_example.py",
    ROOT / "benchmarks/framework_bakeoff/langchain_example.py",
    ROOT / "benchmarks/framework_bakeoff/langgraph_example.py",
    ROOT / "benchmarks/framework_bakeoff/llamaindex_example.py",
]


def run(name: str, command: list[str]) -> dict:
    process = subprocess.run([sys.executable, str(ROOT / "benchmarks" / command[0]), *command[1:]], capture_output=True, text=True)
    status = "EXECUTED" if process.returncode == 0 else "BLOCKED" if "BLOCKED" in process.stdout or "BLOCKED" in process.stderr else "FAILED"
    return {"name": name, "status": status, "returncode": process.returncode, "stdout": process.stdout[-2000:], "stderr": process.stderr[-2000:]}


def main() -> int:
    identity = json.loads((ROOT / "artifacts/phase5_baseline_identity.json").read_text(encoding="utf-8"))
    baseline_integrity = {
        path: hashlib.sha256((ROOT / path).read_bytes()).hexdigest() == record["sha256"]
        for path, record in identity["files"].items()
    }
    dataset_sha256 = hashlib.sha256((ROOT / "artifacts/semantic_benchmark_dataset.json").read_bytes()).hexdigest()
    results = [run(name, command) for name, command in COMMANDS.items()]
    for path in FRAMEWORKS:
        process = subprocess.run([sys.executable, str(path)], capture_output=True, text=True)
        results.append({"name": path.stem, "status": "EXECUTED" if process.returncode == 0 else "BLOCKED" if "BLOCKED" in process.stdout or "BLOCKED" in process.stderr else "FAILED", "returncode": process.returncode, "stdout": process.stdout[-1000:], "stderr": process.stderr[-1000:]})
    overall = "EXECUTED_WITH_BLOCKERS" if any(item["status"] == "BLOCKED" for item in results) else "EXECUTED" if all(item["status"] == "EXECUTED" for item in results) else "FAILED"
    result = {"artifact_type":"phase5b_run_all","status":overall,"timestamp":datetime.now(timezone.utc).isoformat(),"environment":{"python":sys.version,"platform":platform.platform()},"baseline_integrity":baseline_integrity,"dataset_sha256":dataset_sha256,"results":results,"note":"Blocked benchmarks are never converted into passing results."}
    OUTPUT.write_text(json.dumps(result, indent=2, ensure_ascii=False), encoding="utf-8")
    print(json.dumps({"status":overall,"output":str(OUTPUT),"results":[{"name":item["name"],"status":item["status"]} for item in results]}, indent=2))
    return 0 if overall in {"EXECUTED", "EXECUTED_WITH_BLOCKERS"} else 1


if __name__ == "__main__":
    raise SystemExit(main())
