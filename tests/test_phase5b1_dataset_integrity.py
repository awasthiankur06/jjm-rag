import json
from pathlib import Path


def test_phase5b1_dataset_integrity_artifact_exists():
    artifact = Path("d:/jjm-rag/artifacts/phase5b1_dataset_integrity.json")
    assert artifact.exists()

    data = json.loads(artifact.read_text(encoding="utf-8"))
    assert data["gate"] == "PHASE_5B1_REQUIRES_DATASET_REVIEW"
    dataset_summary = data["dataset_summary"]
    assert dataset_summary["semantic_case_count"] == len(data["reconciliation"]["kept_case_ids"])
    assert dataset_summary["candidate_count"] == dataset_summary["unique_unit_id_count"]
    assert data["runner_contract"]["runner_contract_ok"] is True
