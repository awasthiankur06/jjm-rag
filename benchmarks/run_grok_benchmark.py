"""Run the controlled xAI/Grok evidence-grounding benchmark.

Reads XAI_API_KEY only from the environment. The key is never printed or
persisted. Only trimmed evidence for selected cases is sent.
"""
from __future__ import annotations

import argparse
import hashlib
import importlib.util
import importlib.metadata
import json
import os
import platform
import sys
import time
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
POST = ROOT / "artifacts" / "retrieval_evaluation_post_remediation.json"
CASES = ROOT / "artifacts" / "query_evaluation_cases.json"
OUTPUT = ROOT / "artifacts" / "grok_generation_benchmark_runtime.json"
MODEL = "grok-4.6"
INPUT_PRICE = 2.0
OUTPUT_PRICE = 6.0
CASE_IDS = ["Q002", "Q003", "Q009", "Q036", "Q021", "Q014", "Q039"]


def save(status: str, **extra) -> int:
    result = {"artifact_type": "grok_generation_benchmark_runtime", "status": status, "timestamp": datetime.now(timezone.utc).isoformat(), "environment": {"python": sys.version, "platform": platform.platform(), "package_versions": {"openai": importlib.metadata.version("openai") if importlib.util.find_spec("openai") else None}, "xai_key_present": bool(os.environ.get("XAI_API_KEY")), "external_endpoint": "https://api.x.ai/v1"}, **extra}
    OUTPUT.write_text(json.dumps(result, indent=2, ensure_ascii=False), encoding="utf-8")
    print(json.dumps({"status": status, "output": str(OUTPUT), "error": extra.get("error")}, indent=2))
    return 0 if status == "EXECUTED" else 2


def evidence_package(case: dict) -> list[dict]:
    package = []
    for item in case.get("top_k_results", [])[:5]:
        package.append({"evidence_id": item.get("source_id"), "filename": item.get("filename"), "location": item.get("location"), "metadata": item.get("metadata"), "evidence": item.get("evidence", "")[:1600]})
    return package


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--model", default=MODEL)
    args = parser.parse_args()
    if not os.environ.get("XAI_API_KEY"):
        return save("BLOCKED_BY_MISSING_XAI_API_KEY", error="XAI_API_KEY is not present; no external request was made.", cases=CASE_IDS, data_sent="none", query_dataset_sha256=hashlib.sha256(CASES.read_bytes()).hexdigest())
    if importlib.util.find_spec("openai") is None:
        return save("BLOCKED_BY_MISSING_XAI_RUNTIME", error="The isolated openai package is unavailable.", cases=CASE_IDS, data_sent="none")
    from openai import OpenAI
    post = json.loads(POST.read_text(encoding="utf-8"))
    case_map = {case["id"]: case for case in post["cases"]}
    query_map = {case["id"]: case for case in json.loads(CASES.read_text(encoding="utf-8"))["cases"]}
    schema = {"type":"object","additionalProperties":False,"properties":{"answer":{"type":"string"},"status":{"type":"string","enum":["ANSWERED","INSUFFICIENT_EVIDENCE","CONFLICTING_EVIDENCE"]},"claims":{"type":"array","items":{"type":"object","additionalProperties":False,"properties":{"text":{"type":"string"},"evidence_ids":{"type":"array","items":{"type":"string"}},"numeric_value":{"type":["number","string","null"]}},"required":["text","evidence_ids","numeric_value"]}},"limitations":{"type":"array","items":{"type":"string"}}},"required":["answer","status","claims","limitations"]}
    client = OpenAI(api_key=os.environ["XAI_API_KEY"], base_url="https://api.x.ai/v1")
    results = []
    for case_id in CASE_IDS:
        question = query_map.get(case_id, {"query": ""})["query"]
        retrieved = case_map.get(case_id, {})
        package = evidence_package(retrieved)
        prompt = "Answer only from the supplied evidence. Preserve numbers and scope. Cite evidence_ids for every claim. If evidence is insufficient, say so.\n\nQuestion:\n" + question + "\n\nEvidence:\n" + json.dumps(package, ensure_ascii=False)
        started = time.perf_counter()
        try:
            response = client.chat.completions.create(model=args.model, messages=[{"role":"system","content":"You are a grounded JJM evidence answerer."},{"role":"user","content":prompt}], response_format={"type":"json_schema","json_schema":{"name":"grounded_answer","strict":True,"schema":schema}})
            latency_ms = (time.perf_counter() - started) * 1000
            message = response.choices[0].message
            parsed = json.loads(message.content or "{}")
            usage = response.usage
            input_tokens = getattr(usage, "prompt_tokens", None)
            output_tokens = getattr(usage, "completion_tokens", None)
            cost = ((input_tokens or 0) / 1_000_000) * INPUT_PRICE + ((output_tokens or 0) / 1_000_000) * OUTPUT_PRICE
            allowed_ids = {item["evidence_id"] for item in package}
            referenced_ids = {evidence_id for claim in parsed.get("claims", []) for evidence_id in claim.get("evidence_ids", [])}
            results.append({"case_id":case_id,"model":args.model,"request_timestamp":datetime.now(timezone.utc).isoformat(),"latency_ms":latency_ms,"input_tokens":input_tokens,"output_tokens":output_tokens,"estimated_cost_usd":cost,"answer":parsed,"validation":{"structured_output":True,"evidence_references_known":referenced_ids <= allowed_ids,"evidence_ids":sorted(referenced_ids)},"evidence_sent":package})
        except Exception as exc:
            results.append({"case_id":case_id,"model":args.model,"latency_ms":(time.perf_counter()-started)*1000,"error":f"{type(exc).__name__}: {exc}","evidence_sent":package})
    status = "EXECUTED" if results and all("error" not in item for item in results) else "PARTIAL"
    return save(status, model=args.model, cases=results, input_artifact_sha256=hashlib.sha256(POST.read_bytes()).hexdigest(), query_dataset_sha256=hashlib.sha256(CASES.read_bytes()).hexdigest(), data_sent="trimmed retrieved evidence only; complete corpus not sent", pricing={"input_usd_per_million":INPUT_PRICE,"output_usd_per_million":OUTPUT_PRICE})


if __name__ == "__main__":
    raise SystemExit(main())
