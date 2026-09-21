from jjm_rag.production.rag import RagService
from jjm_rag.query_routing.router import QueryRouter
from jjm_rag.retrieval.interfaces import Evidence


def fact(source, metric, value, state, district=None, date="2020", unit="count"):
    return Evidence(source, source, {}, "structured", .9, f"{metric}: {value}", {"metric_name": metric, "value_raw": str(value), "value_numeric": value, "unit": unit, "state": state, "district": district, "report_date": date, "provenance_id": f"p-{source}"})


class Store:
    def __init__(self, facts): self.facts = facts
    def exact(self, q, l): return []
    def lexical(self, q, l): return []
    def structured(self, q, f, l): return self.facts[:l]


class LLM:
    def generate(self, system, user, *, max_tokens, temperature): return {"text": "verified [1][2]"}


def query(facts, text):
    return RagService(Store(facts), llm=LLM()).query(text)


def test_router_preserves_all_named_states_in_multi_geography_query():
    route = QueryRouter().route("What is the combined reported rural population of Assam and Uttar Pradesh on 01/04/2026?")
    assert route.filters["geography"] == "Assam and Uttar Pradesh"


def test_router_keeps_single_geography_query_unchanged():
    route = QueryRouter().route("What is the rural population of Assam on 01/04/2026?")
    assert route.filters == {"geography": "Assam"}


def test_router_preserves_kerala_and_madhya_pradesh_in_r021_query():
    route = QueryRouter().route("Which had more reported households, Thrissur in Kerala or Balaghat in Madhya Pradesh?")
    geography = route.filters["geography"]
    assert "Kerala" in geography
    assert "Madhya Pradesh" in geography
    assert geography != "Kerala"
    assert geography != "Madhya Pradesh"


def test_router_does_not_invent_unrelated_geography_names():
    route = QueryRouter().route("What is the rural population of Assam on 01/04/2026?")
    assert route.filters["geography"] != "Assam and Maharashtra"


def test_duplicate_geography_does_not_fill_two_operands():
    response = query([fact("a", "Population", 10, "Assam"), fact("b", "Population", 11, "Assam")], "What is the difference between Assam and Uttar Pradesh population?")
    assert response.calculation is None
    assert response.confidence["grounded"] is False
    assert any(item["reason"] == "missing requested geography operand" for item in response.calculation_diagnostics["rejected_candidates"])


def test_wrong_metric_family_does_not_fill_operand():
    response = query([fact("a", "Population", 10, "Assam"), fact("b", "Households", 11, "Uttar Pradesh")], "What is the difference between Assam and Uttar Pradesh population?")
    assert response.calculation is None


def test_period_mismatch_abstains():
    response = query([fact("a", "Population", 10, "Assam", date="2020"), fact("b", "Population", 11, "Uttar Pradesh", date="2021")], "What is the difference between Assam and Uttar Pradesh population in 2020?")
    assert response.calculation is None
    assert response.calculation_diagnostics["rejected_candidates"]


def test_units_mismatch_abstains():
    response = query([fact("a", "Population", 10, "Assam", unit="people"), fact("b", "Population", 11, "Uttar Pradesh", unit="%")], "What is the difference between Assam and Uttar Pradesh population?")
    assert response.calculation is None


def test_valid_multiple_geographies_calculate():
    response = query([fact("a", "Population", 10, "Assam"), fact("b", "Population", 11, "Uttar Pradesh")], "What is the difference between Assam and Uttar Pradesh population?")
    assert response.calculation["result"] == 1
    assert len(response.calculation["inputs"]) == 2


def test_percentage_change_requires_two_periods():
    response = query([fact("a", "Connections", 100, "Assam", date="2020"), fact("b", "Connections", 120, "Assam", date="2021")], "What was the percentage change in connections between 2020 and 2021?")
    assert response.calculation["result"] == 20


def test_ranking_without_complete_geography_scope_abstains():
    response = query([fact("a", "Coverage", 90, "Assam")], "Which state had the highest coverage?")
    assert response.calculation is None
    assert response.confidence["grounded"] is False


def test_numeric_geography_identifier_is_not_a_requested_state():
    response = query([fact("a", "Population", 10, "Assam", "35")], "What is the difference between Assam and Uttar Pradesh population?")
    assert response.calculation is None
    assert response.confidence["grounded"] is False


def test_missing_period_operand_abstains():
    response = query([
        fact("a", "House connections", 100, "Sivaganga", date="2020"),
    ], "Compare house connections in Sivaganga between 2020 and 2021.")
    assert response.calculation is None
    assert response.confidence["grounded"] is False


def test_wrong_geography_operand_abstains():
    response = query([
        fact("a", "Population", 10, "Assam"),
        fact("b", "Population", 11, "Assam"),
    ], "What is the difference between Assam and Uttar Pradesh population?")
    assert response.calculation is None
    assert any(item["reason"] == "missing requested geography operand" for item in response.calculation_diagnostics["rejected_candidates"])


def test_wrong_metric_family_abstains():
    response = query([
        fact("a", "Population", 10, "Assam"),
        fact("b", "Households", 11, "Uttar Pradesh"),
    ], "What is the difference between Assam and Uttar Pradesh population?")
    assert response.calculation is None


def test_partial_ranking_candidate_set_abstains():
    response = query([
        fact("a", "Coverage", 90, "Assam"),
    ], "Which state had the highest coverage percentage?")
    assert response.calculation is None
    assert response.confidence["grounded"] is False


def test_multi_geography_operand_acquisition_proceeds():
    response = query([
        fact("a", "Population", 10, "Assam"),
        fact("b", "Population", 11, "Uttar Pradesh"),
    ], "What is the difference between Assam and Uttar Pradesh population?")
    assert response.calculation is not None
    assert len(response.calculation["inputs"]) == 2
    assert {item["state"] for item in response.calculation["inputs"]} == {"Assam", "Uttar Pradesh"}


def test_ru023_style_two_geography_comparison_preserves_exact_operands():
    response = query([
        fact("assam_exact", "Number of Population", 2352118, "Assam", date="01/04/2026"),
        fact("assam_generic", "Population", 33153664, "Assam", date="01/04/2026"),
        fact("up_exact", "Number of Population", 38230635, "Uttar Pradesh", date="01/04/2026"),
        fact("up_generic", "Population", 166888688, "Uttar Pradesh", date="01/04/2026"),
    ], "Which of Assam and Uttar Pradesh had the larger reported rural population on 01/04/2026?")
    assert response.calculation is not None
    assert {item["state"] for item in response.calculation["inputs"]} == {"Assam", "Uttar Pradesh"}
    assert {item["value"] for item in response.calculation["inputs"]} == {2352118, 38230635}
    assert response.calculation["result"] == 35878517


def test_ru025_style_two_geography_sum_still_works():
    response = query([
        fact("assam_exact", "Number of Population", 2352118, "Assam", date="01/04/2026"),
        fact("assam_generic", "Population", 33153664, "Assam", date="01/04/2026"),
        fact("up_exact", "Number of Population", 38230635, "Uttar Pradesh", date="01/04/2026"),
        fact("up_generic", "Population", 166888688, "Uttar Pradesh", date="01/04/2026"),
    ], "What is the combined reported rural population of Assam and Uttar Pradesh on 01/04/2026?")
    assert response.calculation is not None
    assert response.calculation["result"] == 40582753


def test_missing_requested_geography_cannot_be_substituted_by_another_geography():
    response = query([
        fact("assam_exact", "Number of Population", 2352118, "Assam", date="01/04/2026"),
        fact("assam_generic", "Population", 33153664, "Assam", date="01/04/2026"),
        fact("up_generic", "Population", 166888688, "Uttar Pradesh", date="01/04/2026"),
    ], "Which of Assam and Uttar Pradesh had the larger reported rural population on 01/04/2026?")
    assert response.calculation is None
    assert response.confidence["grounded"] is False


def test_non_calculation_queries_keep_standard_fact_behavior():
    response = query([
        fact("assam_exact", "Number of Population", 2352118, "Assam", date="01/04/2026"),
    ], "What rural population was reported for Assam on 01/04/2026?")
    assert response.calculation is None
    assert response.answer_type == "FACT"


def test_multi_period_operand_acquisition_proceeds():
    response = query([
        fact("a", "House connections", 100, "Sivaganga", date="2020"),
        fact("b", "House connections", 120, "Sivaganga", date="2021"),
    ], "Compare house connections in Sivaganga between 2020 and 2021.")
    assert response.calculation is not None
    assert response.calculation["result"] == 20
    assert len(response.calculation["inputs"]) == 2


def test_population_alias_is_compatible():
    response = query([
        fact("a", "Number of Population", 10, "Assam"),
        fact("b", "Population", 11, "Uttar Pradesh"),
    ], "What is the difference between Assam and Uttar Pradesh population?")
    assert response.calculation is not None
    assert response.calculation["result"] == 1


def test_incompatible_units_abstain():
    response = query([
        fact("a", "Population", 10, "Assam", unit="people"),
        fact("b", "Population", 11, "Uttar Pradesh", unit="%"),
    ], "What is the difference between Assam and Uttar Pradesh population?")
    assert response.calculation is None


def test_valid_difference_average_percentage_of_total_still_work():
    difference = query([
        fact("a", "Population", 10, "Assam"),
        fact("b", "Population", 11, "Uttar Pradesh"),
    ], "What is the difference between Assam and Uttar Pradesh population?")
    assert difference.calculation is not None and difference.calculation["result"] == 1

    average = query([
        fact("a", "Population", 10, "Assam"),
        fact("b", "Population", 20, "Uttar Pradesh"),
    ], "What is the average population of Assam and Uttar Pradesh?")
    assert average.calculation is not None and average.calculation["result"] == 15

    percent = query([
        fact("a", "Population", 10, "Assam"),
        fact("b", "Population", 15, "Uttar Pradesh"),
    ], "What percentage of the total population is Assam and Uttar Pradesh?")
    assert percent.calculation is not None and percent.calculation["result"] == 40
