"""Equivalent custom workflow using the validated project abstractions."""
import json
import sys
from pathlib import Path

root = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(root))
from jjm_rag.retrieval.prototype import PrototypeRetriever

artifact = json.loads((root / "artifacts/prototype_manifest.json").read_text(encoding="utf-8"))
retriever = PrototypeRetriever(artifact)
result = retriever.retrieve("What guidance applies to operation and maintenance of rural water supply schemes?", top_k=5)
print({"route": result["route"]["query_type"], "sources": [item["filename"] for item in result["evidence"]], "provenance_preserved": all(item["location"] for item in result["evidence"])})
