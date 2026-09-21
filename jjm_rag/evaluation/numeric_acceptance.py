"""Run provenance-backed numeric acceptance cases against the live service."""
from __future__ import annotations

import argparse
import json
from datetime import datetime, timezone
from decimal import Decimal
from pathlib import Path
from typing import Any

from jjm_rag.production.cli import build_service


def _plain(value: Any) -> Any:
    if isinstance(value, Decimal):
        return int(value) if value == value.to_integral_value() else float(value)
    if isinstance(value, dict):
        return {key: _plain(item) for key, item in value.items()}
    if isinstance(value, list):
        return [_plain(item) for item in value]
    return value


def _scope_matches(actual: dict[str, Any], expected: dict[str, Any]) -> bool:
    return all(actual.get(key) == value for key, value in expected.items())


def evaluate(cases_path: Path, output_path: Path) -> dict[str, Any]:
    cases = json.loads(cases_path.read_text(encoding="utf-8"))["cases"]
    service = build_service()
    results = []
    try:
        for case in cases:
            response = service.query(case["query"], retrieval_only=True)
            result: dict[str, Any] = {"id": case["id"], "kind": case["kind"], "query": case["query"], "pass": False}
            if case["kind"] == "direct_fact":
                facts = response.structured_facts
                matching = [
                    fact for fact in facts
                    if fact["metadata"].get("value_raw") == case["expected_value_raw"]
                    and fact["metadata"].get("metric_name") == case["expected_metric"]
                    and _scope_matches(
                        {"state": fact["metadata"].get("state"), "district": fact["metadata"].get("district")},
                        case["expected_scope"],
                    )
                    and fact["filename"] == case["expected_filename"]
                    and fact["metadata"].get("provenance_id") == case["expected_provenance_id"]
                ]
                result.update({"matched_fact_count": len(matching), "actual_facts": _plain(facts[:10])})
                result["pass"] = bool(matching)
                result["reason"] = "PASS" if matching else "expected fact/value/scope/source/provenance not returned"
            elif case["kind"] == "calculation":
                calculation = response.calculation or {}
                inputs = calculation.get("inputs", [])
                actual_provenance = {item.get("provenance_id") for item in inputs}
                actual_scopes = [{"state": item.get("state"), "district": item.get("district")} for item in inputs]
                result.update({"calculation": _plain(calculation), "actual_scopes": actual_scopes})
                result["pass"] = (
                    calculation.get("validation_status") == "VALIDATED"
                    and calculation.get("operation") == case["expected_operation"]
                    and calculation.get("result") == case["expected_result"]
                    and (not case.get("expected_unit") or calculation.get("result_unit") == case["expected_unit"])
                    and set(case["expected_provenance_ids"]) == actual_provenance
                    and all(scope in actual_scopes for scope in case["expected_scopes"])
                )
                result["reason"] = "PASS" if result["pass"] else "calculation result, unit, scope, or provenance differs"
            else:
                diagnostics = response.calculation_diagnostics or {}
                reasons = [str(item.get("reason", "")) for item in diagnostics.get("rejected_candidates", [])] + list(response.warnings)
                result.update({"answer": response.answer, "reasons": reasons})
                result["pass"] = response.calculation is None and any(case["expected_rejection_reason"] in reason for reason in reasons)
                result["reason"] = "PASS" if result["pass"] else "required abstention reason not observed"
            results.append(result)
    finally:
        session = getattr(getattr(service, "evidence_store", None), "connection", None)
        if session:
            session.close()
    passed = sum(item["pass"] for item in results)
    artifact = {
        "artifact_type": "live_numeric_acceptance_result",
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "input_dataset": str(cases_path),
        "case_count": len(results),
        "passed": passed,
        "failed": len(results) - passed,
        "numeric_accuracy": passed / len(results) if results else "NOT_EVALUABLE",
        "strict_threshold": 1.0,
        "gate": "PASS" if results and passed == len(results) else "FAIL",
        "cases": results,
    }
    output_path.write_text(json.dumps(artifact, indent=2, ensure_ascii=False, default=_plain), encoding="utf-8")
    return artifact


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--cases", type=Path, default=Path("artifacts/numeric_acceptance_cases_v1.json"))
    parser.add_argument("--output", type=Path, default=Path("artifacts/numeric_acceptance_result_v1.json"))
    args = parser.parse_args()
    artifact = evaluate(args.cases, args.output)
    print(json.dumps({key: artifact[key] for key in ("case_count", "passed", "failed", "numeric_accuracy", "gate")}, indent=2))
    return 0 if artifact["gate"] == "PASS" else 1


if __name__ == "__main__":
    raise SystemExit(main())
