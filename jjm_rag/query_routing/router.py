from __future__ import annotations

import re
from dataclasses import dataclass


KNOWN_GEOGRAPHIES = (
    "Assam",
    "Uttar Pradesh",
    "Maharashtra",
    "Madhya Pradesh",
    "Bihar",
    "West Bengal",
    "Odisha",
    "Jharkhand",
    "Punjab",
    "Haryana",
    "Gujarat",
    "Rajasthan",
    "Tamil Nadu",
    "Karnataka",
    "Kerala",
    "Andhra Pradesh",
    "Telangana",
)


@dataclass
class QueryRoute:
    query: str
    intent: str
    strategy: str
    filters: dict[str, str]


class QueryRouter:
    """Simple deterministic router aligned to the approved hybrid retrieval design."""

    def route(self, query: str) -> QueryRoute:
        q = query.lower().strip()
        filters: dict[str, str] = {}

        matched_geographies = [name for name in KNOWN_GEOGRAPHIES if re.search(rf"\b{re.escape(name.lower())}\b", q)]

        # Questions about the mission itself are narrative/policy requests,
        # even when they arrive after a user has selected a source.  Do this
        # before interpreting continuation markers: otherwise "purpose of
        # JJM" can be turned into an unrelated spreadsheet row lookup.
        mission_reference = bool(re.search(r"\b(?:jjm|jal\s+jeevan\s+mission)\b", q))
        mission_question = mission_reference and bool(re.search(
            r"\b(?:what\s+is|what\s+about|purpose|objective|aim|mission|goal|vision|why)\b", q
        ))
        # Follow-up choices are generated from persisted source/header paths.
        # Their control labels ("Selected source", etc.) must not make the
        # next turn look like a source-identification question.
        if mission_question:
            intent = "semantic"
            strategy = "semantic"
        elif re.search(r"\bselected\s+(?:source|metric/header|metric|header)\s*:", q):
            intent = "structured"
            strategy = "structured"
        # A state/district-wise data request asks for rows from a report even
        # when the report title itself includes the word "Format". Handle it
        # before the document-identity/format lookup rules below.
        elif re.search(r"\b(?:state|district)\s*[- ]?wise\b", q) and "data" in q:
            intent = "structured"
            strategy = "structured"
        # ``conversions`` is a J6 numeric field, not a request to compare
        # document versions.  Version routing is therefore word-boundary
        # based for the overloaded token rather than a substring check.
        elif re.search(r"\b(?:version|versions)\b", q) or any(term in q for term in ["duplicate export", "structural variant", "filename suffix", "snapshot"]):
            intent = "version"
            strategy = "version"
        elif "authoritative" in q and "policy" in q and any(term in q for term in ["numeric", "district", "value"]):
            intent = "cross_document"
            strategy = "cross_document"
        elif re.search(r"\b[A-Z]{1,4}\d+[A-Z0-9]*\b", query) and "which" in q and any(term in q for term in ["file", "source"]):
            intent = "exact"
            strategy = "exact"
        elif (q.startswith("which district") or q.startswith("which state")) and any(term in q for term in ["report", "file", "source", "listed"]) and not any(term in q for term in ["highest", "lowest", "coverage", "population", "household", "connection", "scheme", "pws", "village"]):
            # Identifying the scope of a named report is a document-retrieval
            # task, not an aggregate over district/state fact rows.
            intent = "exact"
            strategy = "exact"
        elif any(term in q for term in ["reporting date", "field structure", "fields", "which file", "which source", "which report", "report artifact", "artifact numbered"]):
            intent = "exact"
            strategy = "exact"
        elif re.search(r"\b[A-Z]{2,}\d+[A-Z0-9]*\b", query) and any(term in q for term in ["what does", "say about", "describe", "approval"]):
            # A code-named report asked about narratively benefits from both
            # document and semantic evidence; the code digit is not itself a
            # numeric question.
            intent = "hybrid"
            strategy = "hybrid"
        elif "sanction number" in q and any(term in q for term in ["find", "named", "record"]):
            intent = "exact"
            strategy = "exact"
        elif re.match(r"^\s*(?i:what\s+is|what's|define|definition\s+of|meaning\s+of)\s+(?:the\s+)?[A-Z][A-Z0-9-]{1,}\s*[?!.]*\s*$", query):
            # An acronym definition (for example "What is JJM?") is a
            # narrative/policy request.  It must never fall through to a
            # broad structured scan and return an unrelated numeric row that
            # merely contains the acronym in its report title.
            intent = "semantic"
            strategy = "semantic"
        elif any(phrase in q for phrase in ("what does", "say about", "describe")) and not any(term in q for term in ("how many", "total", "sum", "difference", "percentage of", "compare")):
            # Narrative questions frequently quote a page heading that happens
            # to contain a chapter or page number.  A digit alone must not
            # convert that request into an unrelated structured numeric fact.
            intent = "narrative"
            strategy = "hybrid"
        elif ("compare" in q and (len(matched_geographies) >= 2 or " with " in q or " and " in q)) or ("policy" in q and any(term in q for term in ["numeric", "district", "reported", "value"])):
            intent = "cross_document"
            strategy = "cross_document"
        elif any(term in q for term in ["highest", "lowest", "largest", "smallest", "maximum", "minimum", "ranking"]):
            intent = "structured"
            strategy = "structured"
        elif "which report" not in q and any(term in q for term in ["define", "definition", "objective", "mean in", "guidance", "policy", "responsibilit", "operation and maintenance", "community participation", "monitoring", "surveillance", "operational material"]):
            intent = "semantic"
            strategy = "semantic"
        elif any(term in q for term in ["format", "code", "reference", "field"]):
            intent = "exact"
            strategy = "exact"
        elif any(term in q for term in ["count", "total", "compare", "difference", "sum", "average", "percentage of", "percentage change", "higher", "more", "larger", "highest", "how many", "district", "state", "coverage", "fhtc", "verified", "pending", "completed", "planned", "installed", "geotagged", "population", "households", "connections", "scheme", "schemes", "cost", "costs", "laborator", "as of", "financial year", "fy "]) or any(char.isdigit() for char in q):
            intent = "structured"
            strategy = "structured"
        elif any(term in q for term in ["sanction", "name", "document", "report", "status"]):
            intent = "exact"
            strategy = "exact"
        else:
            intent = "hybrid"
            strategy = "hybrid"

        if matched_geographies:
            filters["geography"] = " and ".join(matched_geographies) if len(matched_geographies) > 1 else matched_geographies[0]
        if "district" in q:
            filters["scope"] = "district"
        if "state" in q:
            filters["scope"] = "state"

        return QueryRoute(query=query, intent=intent, strategy=strategy, filters=filters)
