from benchmarks.run_real_user_evaluation import calculation_accuracy


def case(**calculation):
    return {"calculation_required": True, "expected_calculation": calculation}


def response(**calculation):
    return {"calculation": calculation}


def test_correct_calculation_metadata_is_authoritative():
    assert calculation_accuracy(case(operation="difference", result=5, operand_values=[10, 5], unit="count"), response(operation="difference", result=5, inputs=[{"value": 10, "unit": "count", "provenance_id": "p1"}, {"value": 5, "unit": "count", "provenance_id": "p2"}])) is True


def test_incorrect_result_fails():
    assert calculation_accuracy(case(operation="sum", result=15), response(operation="sum", result=14, inputs=[{"value": 10, "provenance_id": "p1"}, {"value": 5, "provenance_id": "p2"}])) is False


def test_missing_operand_fails():
    assert calculation_accuracy(case(operation="sum", result=15, operand_values=[10, 5]), response(operation="sum", result=15, inputs=[{"value": 10, "provenance_id": "p1"}])) is False


def test_wrong_operation_fails():
    assert calculation_accuracy(case(operation="difference", result=5), response(operation="sum", result=5, inputs=[{"value": 10, "provenance_id": "p1"}, {"value": 5, "provenance_id": "p2"}])) is False


def test_wrong_unit_fails():
    assert calculation_accuracy(case(operation="sum", result=15, unit="households"), response(operation="sum", result=15, inputs=[{"value": 10, "unit": "%", "provenance_id": "p1"}, {"value": 5, "unit": "%", "provenance_id": "p2"}])) is False


def test_provenance_mismatch_or_missing_fails():
    assert calculation_accuracy(case(operation="sum", result=15), response(operation="sum", result=15, inputs=[{"value": 10, "provenance_id": "p1"}, {"value": 5}])) is False
