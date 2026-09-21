# Phase 2 Architecture Decision

## Decision

`ARCHITECTURE_READY_FOR_PROTOTYPE`

This approval covers requirements and a logical architecture only. Implementation has not started.

## Answers to the Approval Questions

1. **Question kinds (`OBSERVED`)**: policy/explanatory questions over two guidance PDFs; exact report, format, state, district, division, habitation, scheme, sanction, and identifier lookups; numeric/table questions; filtered geography/metric/date questions; cross-document comparisons; version/snapshot and provenance questions.
2. **Retrieval methods (`DERIVED`)**: semantic section retrieval for policy; exact lookup for names/codes/format/source identity; structured retrieval for values, totals, ranking, and filters; metadata comparison for versions; hybrid and multi-branch retrieval for cross-document questions.
3. **Semantic-only insufficiency (`DERIVED`)**: yes. Numeric correctness, multi-row headers, total-row handling, exact identifiers, and deterministic comparisons cannot rely on semantic similarity.
4. **Structured storage (`RECOMMENDED`)**: required capability. Store normalized row/metric observations linked to raw source cells, table headers, report scope, and provenance. The storage engine is intentionally undecided.
5. **Canonical entities/fields (`RECOMMENDED`)**: source document, report snapshot, table, header schema, policy section/page, geographic entity, metric observation, raw/normalized values, report format, date/financial year, source status, hash, version relationship, and source location.
6. **Chunking (`RECOMMENDED`)**: PDF section/page/table units; HTML report/table/header-section/row/metric units; schema/header units for templates. No universal token size yet.
7. **Metadata (`RECOMMENDED`)**: filename, hash, detected format, family, source/ingestion status, report title, format code, geography scope, state, district, division, habitation/scheme/sanction identifiers when present, date/financial year, table, row, column path, page, and version evidence.
8. **Provenance (`OBSERVED` + `RECOMMENDED`)**: filename and hash for every source; PDF page and section; HTML report/table/header/row/cell; raw and normalized values; excluded-source audit record.
9. **Query routing (`DERIVED`)**: required as a logical capability because policy, exact, structured, version, and cross-document cases need different evidence paths. A framework is not required.
10. **Orchestration framework (`REQUIRES_VALIDATION`)**: not justified yet. Prototype with plain deterministic components; revisit only if stateful multi-step workflows become complex.
11. **Recommended architecture (`RECOMMENDED`)**: custom Python evidence pipeline with raw-source/provenance layer, structured record capability, exact/metadata lookup, policy semantic retrieval, hybrid router, deterministic computation, evidence validation, and future Grok/xAI synthesis.
12. **Alternatives considered**: framework-centric LangChain, LangGraph, LlamaIndex, xAI native Files/Collections, and a custom stack with selected components.
13. **Why it wins (`DERIVED`)**: it keeps numeric and provenance-critical logic deterministic, supports exact and structured table queries, leaves semantic retrieval replaceable, preserves source hashes and excluded status, and minimizes premature vendor/framework lock-in.
14. **Unknowns (`UNKNOWN`)**: authoritative snapshot ordering, exact policy section segmentation, PDF table extraction fidelity, hidden worksheets, complete schema equivalence across all report variants, and representative user frequency distribution.
15. **Prototype validation (`REQUIRES_VALIDATION`)**: implement read-only extraction of canonical row/metric evidence; execute all 40 cases; measure source recall, exact/filter accuracy, numeric correctness, citations, abstention, latency, and excluded-source safety.

## Option Comparison

| Option | Fit | Strengths | Risks/limits |
|---|---|---|---|
| Custom Python + structured capability + semantic index + future xAI | Best fit | Deterministic tables, exact lookup, provenance, replaceable components, testability | More components to own; structured store choice deferred |
| LangChain | Conditional | Connectors and model abstraction | Does not itself solve schema, numeric correctness, or provenance; extra abstraction |
| LangGraph | Not yet justified | Stateful workflows and retries | Adds orchestration complexity before workflow evidence exists |
| LlamaIndex | Conditional | Document/index abstractions and metadata retrieval | Table semantics and exact numeric computation still require custom paths; coupling risk |
| xAI Files/Collections | Conditional future component | Possible hosted semantic retrieval and Grok integration | Unknown fit for deterministic table queries, source-row provenance, portability, and offline tests |
| Hybrid/custom selected components | Recommended form | Selective use of libraries behind stable interfaces | Requires disciplined interfaces and evaluation |

## Prototype Gate

Before Phase 3 implementation approval, validate:

- every query case has traceable expected evidence;
- excluded `(2)` remains physically present, blocked, excluded, unembedded, and hash-stable;
- structured answers are computed from rows/columns, not generated guesses;
- policy answers cite page/section evidence;
- version answers do not infer order from suffixes;
- missing dates, conflicts, and insufficient evidence produce explicit uncertainty.
