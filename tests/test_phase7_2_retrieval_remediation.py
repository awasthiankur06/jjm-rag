from jjm_rag.ingestion.canonical_persistence import parse_source, persist_canonical_source
from jjm_rag.persistence.database import apply_migration, sqlite_connection
from jjm_rag.production.postgres_store import PostgresEvidenceStore
from jjm_rag.production.rag import RagService
from jjm_rag.production.evaluation_adapter import ProductionEvaluationAdapter
from jjm_rag.query_routing.router import QueryRouter
from jjm_rag.retrieval.interfaces import Evidence
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def test_router_handles_corpus_structured_vocabulary():
    router = QueryRouter()
    assert router.route("Which state has the highest coverage percentage in CS1(A)?").strategy == "structured"
    assert router.route("What chlorination systems are planned, installed, and geotagged for Assam?").strategy == "structured"
    assert router.route("Which report defines the CS1(A) coverage fields?").strategy == "exact"
    assert router.route("Quality report\nSelected source: quality (1).xls").strategy == "structured"
    assert router.route("Remaining conversions to Govt. FHTC for Kokrajhar").strategy == "structured"
    assert router.route("What is JJM?").strategy == "semantic"
    assert router.route("What is the soul purpose of JJM?").strategy == "semantic"
    assert router.route("What about Jal Jeevan Mission?").strategy == "semantic"
    assert router.route("What is JJM?\nSelected source: guidelines.pdf").strategy == "semantic"


def test_fusion_does_not_let_irrelevant_structured_displace_semantic():
    class Store:
        def exact(self, query, limit): return []
        def lexical(self, query, limit): return []
        def structured(self, query, filters, limit): return [Evidence("unrelated", "unrelated.xls", {}, "structured", .99, "unrelated", {})]

    class Semantic:
        def search(self, query, filters, limit): return [Evidence("relevant", "guidance.pdf", {}, "semantic", .6, "relevant", {"provenance_id": "p"})]

    response = RagService(Store(), semantic=Semantic()).query("guidance", retrieval_only=True)
    assert response.evidence[0]["source_id"] == "relevant"


def test_semantic_provider_failure_falls_back_to_deterministic_evidence():
    class Store:
        def exact(self, query, limit): return [Evidence("exact", "guidance.pdf", {}, "exact", .9, "guidance", {})]
        def lexical(self, query, limit): return []
        def structured(self, query, filters, limit): return []

    class FailingSemantic:
        def search(self, query, filters, limit):
            raise RuntimeError("provider unavailable")

    response = RagService(Store(), semantic=FailingSemantic()).query("guidance", retrieval_only=True)
    assert response.evidence[0]["source_id"] == "exact"
    assert "semantic provider unavailable; returned non-semantic evidence only" in response.warnings


def test_fusion_preserves_relevant_candidates_from_multiple_channels():
    class Store:
        def exact(self, query, limit): return [Evidence("exact", "exact.xls", {}, "exact", .9, "exact", {"provenance_id": "p"})]
        def lexical(self, query, limit): return []
        def structured(self, query, filters, limit): return [Evidence(f"noise-{i}", f"noise-{i}.xls", {}, "structured", .99, "noise", {}) for i in range(10)]

    class Semantic:
        def search(self, query, filters, limit): return [Evidence("semantic", "semantic.pdf", {}, "semantic", .8, "semantic", {"provenance_id": "p"})]

    response = ProductionEvaluationAdapter(None, Semantic(), evidence_store=Store()).retrieve("compare guidance with source")
    ids = {item["source_id"] for item in response["evidence"]}
    assert "exact" in ids
    assert "semantic" in ids


def test_postgres_structured_retrieval_uses_header_path_for_coverage_percentages(tmp_path):
    source = tmp_path / "CS1 A. Coverage.xls"
    source.write_text(
        """<html><body><table>
        <tr><th rowspan='2'>State</th><th colspan='3'>FHTCs</th></tr>
        <tr><th>Coverage (in %)</th><th>Coverage (in Nos.)</th><th>Total households</th></tr>
        <tr><td>Assam</td><td>98.50%</td><td>12345</td><td>250000</td></tr>
        <tr><td>West Bengal</td><td>91.20%</td><td>54321</td><td>400000</td></tr>
        </table></body></html>""",
        encoding="utf-8",
    )
    connection = sqlite_connection(":memory:")
    apply_migration(connection, ROOT / "db" / "migrations" / "001_initial_schema.sql")
    document = parse_source(source, "report", {"filename": source.name, "date": "01/04/2026", "financial_year": "2025-26", "format_code": "CS1A"})
    persist_canonical_source(connection, document, {"filename": source.name, "date": "01/04/2026", "financial_year": "2025-26", "format_code": "CS1A"}, "coverage-test")

    results = PostgresEvidenceStore(connection).structured(
        "Which reported state had the highest FHTC coverage percentage in the CS1 A coverage data?",
        {},
        10,
    )
    values = [item.metadata.get("value_numeric") for item in results]
    display_rows = [item.display for item in results]

    assert 98.5 in values
    assert 91.2 in values
    assert 12345 not in values
    assert 250000 not in values
    assert any("Assam" in row for row in display_rows)
    assert any("West Bengal" in row for row in display_rows)


def test_structured_retrieval_honors_complete_source_derived_multiheader_choice(tmp_path):
    source = tmp_path / "habitation_coverage.xls"
    source.write_text(
        """<table>
        <tr><th rowspan='3'>State Name</th><th colspan='6'>PWS Habitations</th></tr>
        <tr><th colspan='3'>With FHTC Coverage = 0 %</th><th colspan='3'>With FHTC Coverage >=100 %</th></tr>
        <tr><th>Habs</th><th>House Holds</th><th>House Connectons</th><th>Habs</th><th>House Holds</th><th>House Connectons</th></tr>
        <tr><td>Karnataka</td><td>3382</td><td>162407</td><td>0</td><td>39741</td><td>6990630</td><td>6990630</td></tr>
        </table>""",
        encoding="utf-8",
    )
    connection = sqlite_connection(":memory:")
    apply_migration(connection, ROOT / "db" / "migrations" / "001_initial_schema.sql")
    document = parse_source(source, "report", {"filename": source.name})
    persist_canonical_source(connection, document, {"filename": source.name}, "header-choice")

    results = PostgresEvidenceStore(connection).structured(
        "Habitation coverage for Karnataka. Selected metric: PWS Habitations -> With FHTC Coverage >=100 % -> House Connectons",
        {"geography": "Karnataka"},
        10,
    )
    assert len(results) == 1
    assert results[0].metadata["value_raw"] == "6990630"
    assert "With FHTC Coverage >=100 %" in results[0].metadata["header_path"]


def test_structured_retrieval_honors_typed_multiheader_path_without_source_marker(tmp_path):
    source = tmp_path / "habitation_coverage.xls"
    source.write_text(
        """<table>
        <tr><th rowspan='3'>State Name</th><th colspan='3'>PWS Habitations</th></tr>
        <tr><th colspan='3'>With FHTC Coverage = 0 %</th></tr>
        <tr><th>Habs</th><th>House Holds</th><th>House Connectons</th></tr>
        <tr><td>Puducherry</td><td>0</td><td>0</td><td>0</td></tr>
        </table>""",
        encoding="utf-8",
    )
    connection = sqlite_connection(":memory:")
    apply_migration(connection, ROOT / "db" / "migrations" / "001_initial_schema.sql")
    document = parse_source(source, "report", {"filename": source.name})
    persist_canonical_source(connection, document, {"filename": source.name}, "typed-header-choice")

    results = PostgresEvidenceStore(connection).structured(
        "PWS Habitations -> With FHTC Coverage = 0 % -> Habs for Puducherry",
        {"geography": "Puducherry"},
        10,
    )
    assert len(results) == 1
    assert results[0].metadata["value_raw"] == "0"


def test_selected_multilevel_population_path_does_not_fall_back_to_generic_total(tmp_path):
    source = tmp_path / "quality_population.xls"
    source.write_text(
        """<table>
        <tr><th rowspan='3'>State Name</th><th colspan='2'>Contamination Wise Number Of Habitations &amp; Population</th></tr>
        <tr><th colspan='2'>Total</th></tr><tr><th>Habs</th><th>Covered with CWPP / IHP</th></tr>
        <tr><td>Maharashtra</td><td>42</td><td>17</td></tr></table>""",
        encoding="utf-8",
    )
    population = tmp_path / "rural_population.xls"
    population.write_text(
        """<table><tr><th>State</th><th>Number of Population</th></tr>
        <tr><td>Jharkhand</td><td>31666928</td></tr></table>""",
        encoding="utf-8",
    )
    connection = sqlite_connection(":memory:")
    apply_migration(connection, ROOT / "db" / "migrations" / "001_initial_schema.sql")
    for item in (source, population):
        document = parse_source(item, "report", {"filename": item.name})
        persist_canonical_source(connection, document, {"filename": item.name}, f"selected-path-{item.name}")

    results = PostgresEvidenceStore(connection).structured(
        "No Of Quality Affected Habitations & Population\nSelected metric/header: Contamination Wise Number Of Habitations & Population -> Total -> Habs",
        {},
        10,
    )
    assert len(results) == 1
    assert results[0].metadata["value_raw"] == "42"
    assert "Contamination Wise" in results[0].metadata["header_path"]
