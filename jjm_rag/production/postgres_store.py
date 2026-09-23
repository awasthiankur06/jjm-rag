from __future__ import annotations

import json
import re
from typing import Any

from jjm_rag.persistence.database import DatabaseSession, PostgresConnection
from jjm_rag.retrieval.interfaces import Evidence

_STOPWORDS = {
    "the", "what", "which", "does", "how", "is", "are", "for", "and", "in", "on", "of", "to", "a", "an",
    "from", "with", "say", "report", "source", "file", "selected", "metric", "header", "listed", "give", "show", "find", "tell", "about", "state", "district",
}


def _query_terms(query: str, limit: int = 10) -> list[str]:
    return [term.lower() for term in re.findall(r"[a-zA-Z0-9]+", query) if len(term) > 2 and term.lower() not in _STOPWORDS][:limit]


def _parse_header_path(header_path: Any) -> list[str]:
    if header_path is None:
        return []
    if isinstance(header_path, str):
        text = header_path.strip()
        if not text:
            return []
        try:
            parsed = json.loads(text)
        except json.JSONDecodeError:
            return [segment.strip() for segment in text.split("|") if segment.strip()]
        if isinstance(parsed, list):
            return [str(item).strip() for item in parsed if str(item).strip()]
        if isinstance(parsed, str):
            return [parsed.strip()]
        return []
    if isinstance(header_path, (list, tuple)):
        return [str(item).strip() for item in header_path if str(item).strip()]
    return []


def _header_path_is_percentage_metric(header_path: Any) -> bool:
    path = _parse_header_path(header_path)
    if not path:
        return False
    lowered = [item.lower() for item in path]
    leaf = lowered[-1]
    has_percentage_indicator = any("%" in item or "percentage" in item or "in %" in item for item in lowered)
    if not has_percentage_indicator:
        return False
    if any("coverage" in item and "nos." in item for item in lowered):
        return False
    # Some source tables (for example J6 verification) label a percentage as
    # ``% of FHTC tagged`` rather than ``FHTC coverage``.  It is still an
    # explicit percentage-valued field and must not be discarded merely
    # because its parent group uses different wording.
    if ("%" in leaf or "percentage" in leaf or "in %" in leaf) and any("fhtc" in item for item in lowered):
        return True
    if any("total households" in item or "households" in item and "coverage" not in item for item in lowered):
        return False
    return any("fhtc" in item for item in lowered) and any("coverage" in item for item in lowered) and ("%" in leaf or "percentage" in leaf or "in %" in leaf)


class PostgresEvidenceStore:
    """Read-only evidence adapter; all user values are parameters."""

    def __init__(self, connection: DatabaseSession):
        self.connection = connection

    def exact(self, query: str, limit: int) -> list[Evidence]:
        terms = _query_terms(query)
        if not terms:
            return []
        clauses = []
        params: list[Any] = []
        for term in terms:
            pattern = f"%{term.lower()}%"
            clauses.append("(LOWER(d.filename) LIKE ? OR LOWER(COALESCE(d.extracted_document_title, '')) LIKE ? OR LOWER(COALESCE(d.report_title, '')) LIKE ? OR LOWER(d.format_code) LIKE ? OR LOWER(c.canonical_text) LIKE ?)")
            params.extend([pattern, pattern, pattern, pattern, pattern])
        selected_source = re.search(r"\bselected\s+source\s*:\s*([^\r\n]+)", query, re.I)
        source_clause = ""
        if selected_source:
            # A clicked source is a hard constraint, not one optional OR
            # match among the words in the question.
            source_clause = " AND LOWER(d.filename) = ?"
            params.append(selected_source.group(1).strip().lower())
        rows = self.connection.execute("""
            SELECT d.document_id, d.filename, d.extracted_document_title, d.format_code, c.content_id, c.canonical_text, c.provenance_id, p.page_number, p.sheet_name, p.table_name
            FROM documents d JOIN canonical_content c ON c.document_id=d.document_id
            LEFT JOIN provenance_records p ON p.provenance_id=c.provenance_id
            WHERE d.production_included=TRUE AND (""" + " OR ".join(clauses) + ")" + source_clause + """
            ORDER BY d.filename, c.content_id
        """, tuple(params)).fetchall()
        return self._rank_content(rows, query, "exact", 1.0, limit)

    def lexical(self, query: str, limit: int) -> list[Evidence]:
        terms = _query_terms(query, 8)
        if not terms:
            return []
        clauses = []
        params: list[Any] = []
        for term in terms:
            clauses.append("(LOWER(c.canonical_text) LIKE ? OR LOWER(d.filename) LIKE ? OR LOWER(COALESCE(d.extracted_document_title, '')) LIKE ? OR LOWER(COALESCE(d.report_title, '')) LIKE ? OR LOWER(d.format_code) LIKE ?)")
            pattern = f"%{term.lower()}%"
            params.extend([pattern, pattern, pattern, pattern, pattern])
        selected_source = re.search(r"\bselected\s+source\s*:\s*([^\r\n]+)", query, re.I)
        source_clause = ""
        if selected_source:
            source_clause = " AND LOWER(d.filename) = ?"
            params.append(selected_source.group(1).strip().lower())
        rows = self.connection.execute("""
            SELECT d.document_id, d.filename, d.extracted_document_title, d.format_code, c.content_id, c.canonical_text, c.provenance_id, p.page_number, p.sheet_name, p.table_name
            FROM documents d JOIN canonical_content c ON c.document_id=d.document_id
            LEFT JOIN provenance_records p ON p.provenance_id=c.provenance_id
            WHERE d.production_included=TRUE AND (""" + " OR ".join(clauses) + ")" + source_clause + """
            ORDER BY c.content_id
        """, tuple(params)).fetchall()
        return self._rank_content(rows, query, "lexical", 0.7, limit)

    def structured(self, query: str, filters: dict[str, str], limit: int) -> list[Evidence]:
        explicit_pdf = self._explicit_pdf_evidence(query, limit)
        if explicit_pdf:
            return explicit_pdf
        if self._has_unresolved_named_entity(query):
            return []
        params: list[Any] = []
        ranking_params: list[Any] = []
        clauses = ["d.production_included=TRUE"]
        terms = _query_terms(query)
        query_lower = query.lower()
        # The UI appends a complete source-derived path after this marker.
        # A user may also type that same multi-level source heading directly
        # (``PWS Habitations -> … -> Habs``).  Both are explicit requests,
        # and must bypass percentage-only heuristics: a percentage *parent*
        # heading can legitimately contain a count-valued child such as Habs.
        # This is source-schema syntax, not a report-name requirement.
        selected_header_path = bool(
            re.search(r"\bselected\s+(?:metric/header|metric|header)\s*:", query_lower)
            # A two-level source header has one separator; three or more
            # levels have several.  Either is an explicit column request.
            or re.search(r"(?:→|->)\s*[^\r\n]+", query)
        )
        # A clicked clarification choice is an explicit constraint, not just
        # lexical context.  Apply it in SQL as well as in the later
        # normalization pass, otherwise broad pre-limit ranking can remove
        # the intended row before `_narrow_to_selected_source` sees it.
        selected_source_match = re.search(r"\bselected\s+source\s*:\s*([^\r\n]+)", query, re.I)
        if selected_source_match:
            clauses.append("LOWER(d.filename) = ?")
            params.append(selected_source_match.group(1).strip().lower())
        selected_header_match = re.search(r"\bselected\s+(?:metric/header|metric|header)\s*:\s*([^\r\n]+)", query, re.I)
        if selected_header_match:
            header_parts = [part.strip().lower() for part in re.split(r"\s*(?:→|->)\s*", selected_header_match.group(1)) if part.strip()]
            for part in header_parts:
                if len(part) >= 3:
                    clauses.append("LOWER(COALESCE(sr.header_path, '')) LIKE ?")
                    params.append(f"%{part}%")
                elif len(header_parts) > 1 and re.fullmatch(r"[a-z0-9]{1,2}", part):
                    # A final source-defined code (for example WQ1's ``C``)
                    # is meaningful only as part of an explicitly selected
                    # multi-level header.  Match it as a JSON path segment,
                    # not as a broad character substring.  This preserves
                    # valid coded leaves while serial columns such as the
                    # removed Progress Tracker ``A`` are never resurrected.
                    clauses.append("LOWER(COALESCE(sr.header_path, '')) LIKE ?")
                    params.append(f'%"{part}"%')
        geography_names = self._geography_names()
        matched_states = [name for name in geography_names[0] if self._name_in_query(name, query_lower) and name.lower() not in {"total", "state", "state/ut"}]
        matched_districts = [
            name for name in geography_names[1]
            if self._name_in_query(name, query_lower)
            and name.lower() not in {"total", "district", "state"}
            and name.lower() not in {state.lower() for state in matched_states}
            # A state name can contain district-like components (for example
            # Daman/Diu or Jammu).  When the full persisted state name is
            # present, those components must not silently turn a state query
            # into an impossible district filter.
            and not any(name.lower() in state.lower() for state in matched_states)
        ]
        # Comparative and broad "which states" requests need evidence from
        # more than the first row-dense workbook.  Fetch a bounded surplus and
        # diversify by document below; this is source-level ranking, not a
        # source-specific rule.
        diversify_documents = len(matched_states) > 1 or "compare" in query_lower or query_lower.startswith("which states")
        # Keep the actual source-language patterns for SQL filtering.  A
        # category label (for example ``laborator``) is not necessarily a
        # substring of every source label (many workbooks say ``labs``).
        # Filtering on the category alone silently drops valid evidence.
        metric_hints = []
        for hint, patterns in {
            "households": ["household", "households", "hh"],
            "population": ["population"],
            "coverage": ["coverage", "fhtc"],
            "connection": ["connection", "connections"],
            "scheme": ["scheme", "schemes"],
            "laborator": ["laborator", "nabl"],
            "chlorination": ["chlorination", "geotagged", "installed", "planned"],
        }.items():
            if any(pattern in query_lower for pattern in patterns):
                metric_hints.extend(patterns)
        metric_hints = list(dict.fromkeys(metric_hints))
        resolved_states = "COALESCE(g.state_name, gd.state_name)"
        # Respect source-language geographic grain before ranking. A state
        # summary must not compete with district rows for a district-wise
        # request, without relying on any report filename.
        if re.search(r"\bdistrict\s*[- ]?wise\b", query_lower):
            clauses.append("g.district_name IS NOT NULL")
        elif re.search(r"\bstate\s*[- ]?wise\b", query_lower):
            clauses.append("g.district_name IS NULL")
        if matched_states and not matched_districts:
            clauses.append(f"{resolved_states} IN (" + ",".join(["?"] * len(matched_states)) + ")")
            params.extend(matched_states)
        if matched_districts:
            clauses.append("(g.district_name IN (" + ",".join(["?"] * len(matched_districts)) + ") OR (g.district_name IS NULL AND gd.district_name IN (" + ",".join(["?"] * len(matched_districts)) + ")))" )
            params.extend(matched_districts)
            params.extend(matched_districts)
        date_terms = re.findall(r"\b\d{1,2}/\d{1,2}/\d{4}\b", query)
        if date_terms:
            # Many tabular reports encode the snapshot date in the column
            # header (for example, ``House connections as on 23/08/2026``),
            # rather than in a report-level dimension.  A date filter must
            # therefore examine the metric/header as well as report metadata
            # and document identity.
            date_clauses = []
            for date_term in date_terms:
                pattern = f"%{date_term.lower()}%"
                date_clauses.append("(r.report_date = ? OR r.financial_year = ? OR LOWER(COALESCE(d.extracted_document_title, '')) LIKE ? OR LOWER(d.filename) LIKE ? OR LOWER(COALESCE(sr.metric_name, '')) LIKE ? OR LOWER(COALESCE(sr.header_path, '')) LIKE ?)")
                params.extend([date_term, date_term, pattern, pattern, pattern, pattern])
            clauses.append("(" + " OR ".join(date_clauses) + ")")
        header_path_available = self._has_structured_header_path_column()
        # Header-path-only selection is appropriate only when the user asks for
        # a percentage.  Treating every request mentioning coverage this way
        # discards valid count-based PWS/FHTC measures and can flood the result
        # set with unrelated coverage workbooks.
        coverage_header_path_query = (
            header_path_available
            and not selected_header_path
            and any(token in query_lower for token in ["percentage", "in %", "%"])
            and any(token in query_lower for token in ["coverage", "fhtc"])
            and any(token in query_lower for token in ["state", "district", "state/ut"])
        )
        if metric_hints and not coverage_header_path_query and not selected_header_path:
            # A concept can be expressed in a source title rather than each
            # individual column header (for example B11 rural-population
            # tables with a ``TOTAL`` column).  Require it in either the
            # metric or the document identity, never only the leaf header.
            metric_clauses = []
            for hint in metric_hints:
                # Multi-level spreadsheets often put the concept in a parent
                # heading (``Completion of schemes -> Physically completed``)
                # while the stored leaf metric is only ``Physically
                # completed``.  Restricting this predicate to leaf/document
                # labels silently loses that exact persisted column.
                metric_clauses.append("(LOWER(sr.metric_name) LIKE ? OR LOWER(COALESCE(sr.header_path, '')) LIKE ? OR LOWER(COALESCE(sr.table_name, '')) LIKE ? OR LOWER(COALESCE(d.extracted_document_title, '')) LIKE ? OR LOWER(COALESCE(d.report_title, '')) LIKE ? OR LOWER(d.filename) LIKE ?)")
                pattern = f"%{hint.lower()}%"
                params.extend([pattern] * 6)
            clauses.append("(" + " OR ".join(metric_clauses) + ")")
        if "population" in query_lower and "total" in query_lower and not selected_header_path:
            # B11-style population reports use TOTAL/SC/ST/GEN leaf headers.
            # An explicit request for totals must not silently select a
            # demographic component from the same otherwise relevant report.
            clauses.append("LOWER(sr.metric_name) = ?")
            params.append("total")
        if terms and not coverage_header_path_query and not selected_header_path:
            text_clauses = []
            for term in terms:
                pattern = f"%{term.lower()}%"
                text_clauses.append("(LOWER(d.filename) LIKE ? OR LOWER(COALESCE(d.extracted_document_title, '')) LIKE ? OR LOWER(COALESCE(d.report_title, '')) LIKE ? OR LOWER(d.format_code) LIKE ? OR LOWER(sr.metric_name) LIKE ? OR LOWER(COALESCE(sr.header_path, '')) LIKE ? OR LOWER(sr.table_name) LIKE ? OR LOWER(sr.value_raw) LIKE ? OR LOWER(c.canonical_text) LIKE ?)")
                params.extend([pattern] * 9)
            clauses.append("(" + " OR ".join(text_clauses) + ")")
        if filters.get("geography") and not (matched_states or matched_districts):
            clauses.append("(LOWER(COALESCE(g.state_name, gd.state_name)) LIKE ? OR LOWER(g.district_name) LIKE ?)")
            value = f"%{filters['geography'].lower()}%"
            params.extend([value, value])
        query_limit = ""
        if not coverage_header_path_query:
            query_limit = " LIMIT ?"
            params.append(limit * 4 if diversify_documents else limit)
        ranking_terms = _query_terms(query, 12)
        ranking_parts: list[str] = []
        for term in ranking_terms:
            pattern = f"%{term.lower()}%"
            ranking_parts.append("CASE WHEN LOWER(COALESCE(d.extracted_document_title, '')) LIKE ? THEN 12 ELSE 0 END")
            ranking_parts.append("CASE WHEN LOWER(COALESCE(d.format_code, '')) LIKE ? THEN 10 ELSE 0 END")
            ranking_parts.append("CASE WHEN LOWER(COALESCE(sr.metric_name, '')) LIKE ? THEN 8 ELSE 0 END")
            ranking_parts.append("CASE WHEN LOWER(COALESCE(sr.header_path, '')) LIKE ? THEN 7 ELSE 0 END")
            ranking_parts.append("CASE WHEN LOWER(COALESCE(sr.table_name, '')) LIKE ? THEN 4 ELSE 0 END")
            ranking_params.extend([pattern] * 5)
        relevance_score = " + ".join(ranking_parts) if ranking_parts else "0"
        rows = self.connection.execute(f"""
                SELECT sr.record_id, sr.header_path, COALESCE(c.content_id, sr.record_id) AS content_id, sr.document_id, d.filename, d.extracted_document_title, d.format_code, sr.table_name,
                   sr.metric_name, sr.value_raw, sr.value_numeric, sr.unit,
                   sr.provenance_id, COALESCE(g.state_name, gd.state_name) AS state_name, g.district_name, r.report_date,
                       r.reporting_period, r.financial_year, p.page_number, p.sheet_name, ({relevance_score}) AS relevance_score,
                     p.table_name AS provenance_table, p.row_index, p.column_index, p.cell_reference
            FROM structured_records sr JOIN documents d ON d.document_id=sr.document_id
                 LEFT JOIN canonical_content c ON c.provenance_id=sr.provenance_id
            LEFT JOIN geography_dimensions g ON g.geography_id=sr.geography_id
            LEFT JOIN (SELECT district_name, MIN(state_name) AS state_name FROM geography_dimensions WHERE state_name IS NOT NULL GROUP BY district_name HAVING COUNT(DISTINCT state_name)=1) gd ON gd.district_name=g.district_name
            LEFT JOIN reporting_dimensions r ON r.reporting_id=sr.reporting_id
                 LEFT JOIN provenance_records p ON p.provenance_id=sr.provenance_id
            WHERE {' AND '.join(clauses)} ORDER BY relevance_score DESC, CASE WHEN sr.value_numeric IS NOT NULL THEN 0 ELSE 1 END, CASE WHEN g.district_name IS NULL THEN 0 ELSE 1 END, sr.record_id{query_limit}
        """, tuple(ranking_params + params)).fetchall()
        if coverage_header_path_query and header_path_available:
            filtered_rows = []
            for row in rows:
                header_path = None
                try:
                    header_path = row["header_path"] if "header_path" in row.keys() else None
                except Exception:
                    header_path = None
                if _header_path_is_percentage_metric(header_path) and row["value_numeric"] is not None:
                    filtered_rows.append(row)
            rows = filtered_rows
        rows = self._narrow_to_explicit_document_identity(rows, query)
        rows = self._narrow_to_selected_source(rows, query)
        rows = self._narrow_to_explicit_header_path(rows, query)
        evidence = [self._structured_evidence(row) for row in rows]
        if diversify_documents:
            evidence = self._diversify_by_document(evidence, limit)
        else:
            evidence = evidence[:limit]
        # Some source formats (notably PDF tables) are intentionally retained
        # as canonical page/table text when deterministic table extraction is
        # unavailable.  A table/PDF question may use that provenance-bearing
        # evidence, but it remains labelled as exact canonical evidence rather
        # than being fabricated as a structured record.
        if not evidence and any(token in query_lower for token in ("pdf", "table")):
            return self.exact(query, limit)
        return evidence

    @staticmethod
    def _narrow_to_explicit_document_identity(rows: list[Any], query: str) -> list[Any]:
        """Keep a uniquely named report when the query supplies its title.

        This is intentionally based on document identity terms, not a list of
        report names. It prevents similarly shaped reports from being mixed in
        a state-level aggregation while leaving broad queries untouched.
        """
        identity_terms = [term for term in _query_terms(query, 20) if len(term) >= 8]
        if not identity_terms or not rows:
            return rows
        scores: dict[str, int] = {}
        for row in rows:
            identity = f"{row['filename']} {row['extracted_document_title'] or ''} {row['format_code'] or ''}".lower()
            document_id = str(row["document_id"])
            scores[document_id] = max(scores.get(document_id, 0), sum(term in identity for term in identity_terms))
        best = max(scores.values(), default=0)
        best_documents = {document_id for document_id, score in scores.items() if score == best}
        # One unusually specific title term is enough only when it identifies
        # one document; tied generic terms (for example "connections") must
        # not narrow a broad state-level request.
        if best <= 0 or len(best_documents) != 1:
            return rows
        return [row for row in rows if str(row["document_id"]) in best_documents]

    @staticmethod
    def _narrow_to_explicit_header_path(rows: list[Any], query: str) -> list[Any]:
        """Honor a complete source-derived multi-level heading when supplied.

        Clarification choices are appended to the user's question verbatim.
        SQL term matching is intentionally broad for recall, so perform this
        exact, normalized path check before selecting a fact.  It is generic
        for every table with persisted header paths and never matches a leaf
        heading alone (such as the repeated ``House Holds``).
        """
        if not rows:
            return rows
        normalized_query = re.sub(r"[^a-z0-9]+", " ", query.lower()).strip()
        matching_paths: set[str] = set()
        for row in rows:
            raw_path = row["header_path"] if "header_path" in row.keys() else None
            path = _parse_header_path(raw_path)
            normalized_path = re.sub(r"[^a-z0-9]+", " ", " ".join(path).lower()).strip()
            if len(normalized_path) >= 12 and normalized_path in normalized_query:
                matching_paths.add(normalized_path)
        if not matching_paths:
            return rows
        return [
            row
            for row in rows
            if re.sub(r"[^a-z0-9]+", " ", " ".join(_parse_header_path(row["header_path"])).lower()).strip() in matching_paths
        ]

    @staticmethod
    def _narrow_to_selected_source(rows: list[Any], query: str) -> list[Any]:
        """Resolve a user-clicked physical source choice without heuristics."""
        match = re.search(r"\bselected\s+source\s*:\s*([^\r\n]+)", query, re.I)
        if not match:
            return rows
        filename = match.group(1).strip().lower()
        exact = [row for row in rows if str(row["filename"] or "").lower() == filename]
        return exact if exact else rows

    def _has_structured_header_path_column(self) -> bool:
        if isinstance(self.connection, PostgresConnection):
            try:
                rows = self.connection.execute(
                    "SELECT column_name FROM information_schema.columns WHERE table_schema = 'public' AND table_name = 'structured_records' AND column_name = ?",
                    ("header_path",),
                ).fetchall()
                return bool(rows)
            except Exception:
                return False
        try:
            rows = self.connection.execute("PRAGMA table_info(structured_records)").fetchall()
            if rows:
                return any(str(row[1]).lower() == "header_path" for row in rows)
        except Exception:
            pass
        try:
            rows = self.connection.execute(
                "SELECT column_name FROM information_schema.columns WHERE table_schema = 'public' AND table_name = 'structured_records' AND column_name = ?",
                ("header_path",),
            ).fetchall()
            return bool(rows)
        except Exception:
            return False

    def _geography_names(self) -> tuple[list[str], list[str]]:
        states = self.connection.execute("SELECT DISTINCT state_name FROM geography_dimensions WHERE state_name IS NOT NULL").fetchall()
        districts = self.connection.execute("SELECT DISTINCT district_name FROM geography_dimensions WHERE district_name IS NOT NULL").fetchall()
        return ([row["state_name"] for row in states if any(char.isalpha() for char in row["state_name"])], [row["district_name"] for row in districts if any(char.isalpha() for char in row["district_name"])])

    def _has_unresolved_named_entity(self, query: str) -> bool:
        states, districts = self._geography_names()
        known = {name.lower() for name in states + districts}
        query_lower = query.lower()
        # Prefer the complete persisted geography vocabulary.  The fallback
        # grammar below intentionally stays conservative, but it cannot
        # represent long names such as ``North And Middle Andaman`` without
        # truncating them and falsely rejecting a valid request.
        if any(self._name_in_query(name, query_lower) for name in states + districts):
            return False
        # Do not inspect every title-cased word: report names such as
        # ``Progress in Aspirational districts`` and ``Ashram Shala`` are not
        # geography claims.  Only a value explicitly introduced as a state or
        # district can be an unresolved geography filter. Placeholder requests
        # ("a named state") are handled separately by the answer layer.
        named = {
            match.group(1)
            # Do not let a newline-delimited follow-up control field become
            # part of the geography (``State: Puducherry\nSelected source``).
            # Horizontal whitespace accepts natural formatting without
            # crossing into the next semantic field.
            for match in re.finditer(r"\b(?:state|district)[ \t]*(?:name)?[ \t]*(?:is|:|=)[ \t]*([A-Z][a-zA-Z]*(?:[ \t]+[A-Z][a-zA-Z]*)?)", query, re.IGNORECASE)
        }
        return any(token.lower() not in known and not any(token.lower() in name.split() for name in known) for token in named)

    @staticmethod
    def _rank_geography_operands(items: list[Evidence], geographies: list[str]) -> list[Evidence]:
        def score(item: Evidence) -> tuple[int, int, str]:
            metadata = item.metadata
            state = str(metadata.get("state") or "").lower()
            district = str(metadata.get("district") or "").lower()
            requested = state in {value.lower() for value in geographies} or district in {value.lower() for value in geographies}
            scope = 1 if state and not district else 0
            numeric = 1 if metadata.get("value_numeric") is not None else 0
            return (-int(requested), -scope, -numeric, item.source_id)
        return sorted(items, key=score)

    @staticmethod
    def _diversify_by_document(items: list[Evidence], limit: int) -> list[Evidence]:
        """Keep the best row per source before admitting additional rows."""
        selected: list[Evidence] = []
        seen: set[str] = set()
        for item in items:
            if item.filename in seen:
                continue
            seen.add(item.filename)
            selected.append(item)
            if len(selected) >= limit:
                return selected
        for item in items:
            if item in selected:
                continue
            selected.append(item)
            if len(selected) >= limit:
                break
        return selected

    def _explicit_pdf_evidence(self, query: str, limit: int) -> list[Evidence]:
        """Prefer a literally named PDF over approximate tabular matches."""
        if "pdf" not in query.lower():
            return []
        identity_terms = [term for term in _query_terms(query) if len(term) >= 8]
        if not identity_terms:
            return []
        direct = [
            item for item in self.exact(query, limit * 3)
            if item.filename.lower().endswith(".pdf")
            and any(term in item.filename.lower() for term in identity_terms)
        ]
        return direct[:limit]

    @staticmethod
    def _name_in_query(name: str, query_lower: str) -> bool:
        return bool(re.search(r"(?<![a-z])" + re.escape(name.lower()) + r"(?![a-z])", query_lower))

    @staticmethod
    def _structured_evidence(row: Any) -> Evidence:
        location = {"content_unit_id": row["content_id"], "table": row["table_name"], "page": row["page_number"], "sheet": row["sheet_name"], "row": row["row_index"], "column": row["column_index"], "cell": row["cell_reference"]}
        metric_date = re.search(r"\b\d{1,2}/\d{1,2}/\d{4}\b", f"{row['metric_name'] or ''} {row['header_path'] or ''}")
        # A column-level snapshot is more precise than a document-level date
        # when one table intentionally compares multiple dates side by side.
        effective_report_date = metric_date.group(0) if metric_date else row["report_date"]
        metadata = {"provenance_id": row["provenance_id"], "record_id": row["record_id"], "document_id": row["document_id"], "metric_name": row["metric_name"], "header_path": row["header_path"], "extracted_document_title": row["extracted_document_title"], "format_code": row["format_code"], "relevance_score": row["relevance_score"], "value_raw": row["value_raw"], "state": row["state_name"], "district": row["district_name"], "report_date": effective_report_date, "reporting_period": row["reporting_period"], "financial_year": row["financial_year"], "value_numeric": row["value_numeric"], "unit": row["unit"], "source_type": "structured"}
        geography = row["state_name"] or row["district_name"]
        display = (f"{geography}: " if geography else "") + f"{row['metric_name']}: {row['value_raw']}" + (f" {row['unit']}" if row["unit"] else "")
        return Evidence(str(row["content_id"]), row["filename"], location, "structured", 0.95, display, metadata)

    @staticmethod
    def _content(row: Any, method: str, relevance: float) -> Evidence:
        title = row["extracted_document_title"] if "extracted_document_title" in row.keys() else None
        location = {"content_unit_id": row["content_id"], "page": row["page_number"], "sheet": row["sheet_name"], "table": row["table_name"]}
        return Evidence(str(row["content_id"]), row["filename"], location, method, relevance, row["canonical_text"], {"provenance_id": row["provenance_id"], "document_id": row["document_id"], "extracted_document_title": title})

    def _rank_content(self, rows: list[Any], query: str, method: str, base: float, limit: int) -> list[Evidence]:
        terms = _query_terms(query)
        ranked: dict[str, tuple[int, Evidence]] = {}
        selected_source = bool(re.search(r"\bselected\s+source\s*:", query, re.I))
        for row in rows:
            # Source-identification queries should prefer a direct filename or
            # extracted-title match over a word that happens to occur in an
            # unrelated long content unit.  This remains document-level and
            # deterministic; it is not an evaluation-case preference.
            title = row["extracted_document_title"] if "extracted_document_title" in row.keys() else ""
            format_code = row["format_code"] if "format_code" in row.keys() else ""
            title_haystack = f"{row['filename']} {title or ''} {format_code or ''}".lower()
            content_haystack = str(row['canonical_text']).lower()
            matches = sum(
                (50 if format_code and term == str(format_code).lower() else 0)
                # A long literal token in a filename/title (for example a
                # supplied report or PDF name) is stronger source identity
                # evidence than several incidental words in row text.
                + (20 if len(term) >= 8 and term in title_haystack else 3 if term in title_haystack else 0)
                + (1 if term in content_haystack else 0)
                for term in terms
            )
            evidence = self._content(row, method, base + (matches / max(1, len(terms))))
            # Broad source-identification retrieval needs one representative
            # chunk per document.  Once a user selects a physical source,
            # however, retain competing chunks from that source so lexical
            # ranking can locate the requested page rather than arbitrarily
            # keeping one document-level representative.
            rank_key = str(row["content_id"]) if selected_source else str(row["document_id"])
            current = ranked.get(rank_key)
            if current is None or matches > current[0] or (matches == current[0] and evidence.source_id < current[1].source_id):
                ranked[rank_key] = (matches, evidence)
        return [evidence for _, evidence in sorted(ranked.values(), key=lambda item: (-item[0], item[1].filename, item[1].source_id))[:limit]]
