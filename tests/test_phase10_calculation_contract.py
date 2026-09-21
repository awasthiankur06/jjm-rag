from benchmarks.run_real_user_evaluation import calculation_accuracy
from jjm_rag.production.rag import RagService
from jjm_rag.retrieval.interfaces import Evidence


def calculation(**kwargs):
    return {"calculation_required": True, "expected_calculation": kwargs}


def response(**kwargs):
    return {"calculation": kwargs}


def test_result_unit_and_provenance_are_required():
    assert calculation_accuracy(calculation(operation="sum", result=15, unit="households"), response(operation="sum", result=15, result_unit="households", inputs=[{"value": 10, "unit": "households", "provenance_id": "p1"}, {"value": 5, "unit": "households", "provenance_id": "p2"}])) is True


def test_missing_result_unit_is_allowed_when_expected_unit_unspecified():
    assert calculation_accuracy(calculation(operation="sum", result=15), response(operation="sum", result=15, inputs=[{"value": 10, "provenance_id": "p1"}, {"value": 5, "provenance_id": "p2"}])) is True


def test_incorrect_operation_and_operand_values_fail():
    assert calculation_accuracy(calculation(operation="percentage_of_total", result=40, operand_values=[10, 15]), response(operation="sum", result=25, inputs=[{"value": 10, "provenance_id": "p1"}, {"value": 15, "provenance_id": "p2"}])) is False


class Store:
    def __init__(self, facts): self.facts = facts
    def exact(self, query, limit): return []
    def lexical(self, query, limit): return []
    def structured(self, query, filters, limit): return self.facts[:limit]


class LLM:
    def generate(self, system, user, *, max_tokens, temperature): return {"text": "Result [1][2]."}


def fact(source, metric, value, state, district=None, date="2020", unit="count"):
    return Evidence(source, "report.xls", {}, "structured", 1, "fact", {"metric_name": metric, "value_raw": str(value), "value_numeric": value, "unit": unit, "state": state, "district": district, "report_date": date, "provenance_id": f"p-{source}"})


def test_duplicate_geography_cannot_fill_two_operands():
    response = RagService(Store([fact("a", "Population", 10, "Alpha")]), llm=LLM()).query("What is the difference between Alpha and Beta population?")
    assert response.calculation is None
    assert response.confidence["grounded"] is False


def test_multi_period_requires_each_explicit_period():
    response = RagService(Store([fact("a", "Connections", 10, "Alpha", date="2020")]), llm=LLM()).query("What is the percentage change in connections between 2020 and 2021?")
    assert response.calculation is None


def test_population_aliases_are_compatible_at_state_scope():
    facts = [fact("a", "Number of Population", 10, "Alpha", unit=None), fact("b", "Population", 20, "Beta", unit=None)]
    response = RagService(Store(facts), llm=LLM()).query("What is the combined population of Alpha and Beta?")
    assert response.calculation["result"] == 30
    assert {item["state"] for item in response.calculation["inputs"]} == {"Alpha", "Beta"}


def test_partial_ranking_candidate_set_abstains():
    response = RagService(Store([fact("a", "Coverage", 10, "Alpha", unit="%")]), llm=LLM()).query("Which state has the highest coverage percentage?")
    assert response.calculation is None


def test_incompatible_units_abstain_before_calculation():
    facts = [fact("a", "Population", 10, "Alpha", unit="people"), fact("b", "Population", 20, "Beta", unit="households")]
    response = RagService(Store(facts), llm=LLM()).query("What is the combined population of Alpha and Beta?")
    assert response.calculation is None
