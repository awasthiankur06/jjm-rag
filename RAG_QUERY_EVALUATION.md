# Query Evaluation Set for the JJM RAG Architecture

This document contains a realistic evaluation set derived from the actual corpus and expected user behavior.

## 1. Query Classification

The queries below cover:

- policy guidance questions
- exact lookup questions
- state-level and district-level questions
- numeric and comparison questions
- version/snapshot questions
- sanction/document reference questions
- spreadsheet-only questions
- cross-document questions
- multi-step retrieval questions

---

## 2. Representative Query Matrix

| ID | Question | Expected source | Expected information unit | Required retrieval method | Exact match needed | Semantic retrieval needed | Filtering required | Structured query required | Expected citation granularity |
|---|---|---|---|---|---|---|---|---|---|
| Q1 | What does the JJM operational guidance say about program definitions or process standards? | policy PDF | section/subsection | semantic + keyword | No | Yes | No | No | section |
| Q2 | Which state has the highest FHTC coverage according to the coverage reports? | coverage summary table | table row | structured + hybrid | No | No | state + metric | Yes | row |
| Q3 | What is the verified scheme count for Assam in the progress tracker? | progress tracker file | report row | exact + structured | Yes | No | state + date | Yes | row |
| Q4 | Which districts are showing the highest pending schemes? | progress tracker file | table rows | structured + exact | No | No | district + status | Yes | table rows |
| Q5 | Provide the beneficiary verification status for a given division or district. | beneficiary verification file | row | exact + structured | Yes | No | geography | Yes | row |
| Q6 | Which file contains the latest sanction order listing? | sanction order table | document/table | metadata + exact | Yes | No | document type | No | document/table |
| Q7 | Find the sanction order references associated with a given scheme category. | sanction list | row/table | exact | Yes | No | category | No | row |
| Q8 | Which files are version variants of the same progress tracker report? | multiple files | document metadata | metadata + hash comparison | Yes | No | document family | No | document |
| Q9 | What is the population benchmark for Assam or another named state? | benchmark demographic table | row | exact + structured | Yes | No | geography | Yes | row |
| Q10 | Compare district population totals within a specified state. | demographic table | table section | structured | No | No | geography | Yes | table/rows |
| Q11 | Which report tracks school water-supply status? | school status file | doc/table | exact + metadata | Yes | No | report type | No | document/table |
| Q12 | Show the water quality and chlorination-related records for the relevant report family. | quality/chlorination files | table rows | exact + structured | Yes | No | report family + metric | Yes | row |
| Q13 | Which file covers geo-tagged water sources? | geo-tagged status report | doc/table | exact + metadata | Yes | No | report type | No | document/table |
| Q14 | What is the format code for the water source infrastructure report? | template form file | schema/form metadata | exact | Yes | No | report family | No | document/table |
| Q15 | What are the latest district progress figures in the district-level tracker? | district progress report | table | structured + metadata | Yes | No | date/version | Yes | row/table |
| Q16 | How does the guidance define FHTC operationally? | policy PDF | section | semantic | No | Yes | concept term | No | section |
| Q17 | Which policy document explains quality or coverage definitions? | policy PDF | section | semantic + keyword | No | Yes | concept term | No | section |
| Q18 | What is the difference between the state-level population report and the district-level population report? | benchmark files | table comparison | hybrid + metadata | No | Yes | geography + report family | Yes | table/document |
| Q19 | Which files look like templates rather than final reports? | form/template files | document metadata | metadata + exact | Yes | No | file family | No | document |
| Q20 | Which files are likely duplicates or revisions of the same underlying dataset? | multiple files | document metadata | metadata + content hash | Yes | No | family + snapshot | No | document |
| Q21 | Which report contains sanction-order references and external document links? | sanction list file | table | exact + metadata | Yes | No | sanction / document reference | No | table/row |
| Q22 | For a given state, what are the verified, pending, and completed scheme counts? | progress tracker | row/table | structured + exact | Yes | No | state + metric | Yes | row |
| Q23 | What is the current coverage status in a specific geography and which report provides it? | coverage report + policy context | hybrid | hybrid retrieval | No | Yes | geography + metric | Yes | table + section |
| Q24 | What is the historical relationship between the different versions of the progress tracker? | multiple revision files | snapshot metadata | metadata + version logic | Yes | No | report family + version | No | document |
| Q25 | Is a value in one report derived from a statewide benchmark or from a direct district record? | multiple files | row / table source | metadata + structured | Yes | No | geography + metric | Yes | row |
| Q26 | What is the status of water supply in schools for a specific geographic area? | school status file | table row | exact + structured | Yes | No | geography + metric | Yes | row |
| Q27 | Which report tracks the number of quality-affected habitations? | template / status file | table or form | exact + metadata | Yes | No | report family | No | document/table |
| Q28 | Which policy or report defines the term PWS or FHTC in this corpus? | policy + coverage files | section / table | hybrid | No | Yes | concept type | No | section/table |
| Q29 | Show the latest record for the verification tracker and explain the difference from older versions. | multiple revision files | table + snapshot metadata | hybrid + metadata | Yes | No | version/date | Yes | row/document |
| Q30 | Which district or division has the highest pending verification count? | progress tracker | table row | structured + exact | Yes | No | status + geography | Yes | row |

---

## 3. Query Category Coverage

This evaluation set covers:

- policy/guidance queries: Q1, Q16, Q17, Q28
- exact identifier lookup: Q6, Q7, Q11, Q14, Q19, Q21
- state-level queries: Q2, Q3, Q9, Q22, Q23
- district-level queries: Q4, Q5, Q10, Q15, Q30
- table lookup: Q11, Q12, Q13, Q21, Q26, Q27
- numeric questions: Q2, Q3, Q4, Q9, Q10, Q12, Q15, Q22, Q30
- comparison questions: Q10, Q18, Q25, Q29
- aggregation questions: Q2, Q3, Q4, Q22, Q30
- date/version questions: Q8, Q15, Q24, Q29
- sanction/document reference lookup: Q6, Q7, Q21
- cross-document questions: Q18, Q23, Q25, Q29
- multi-step retrieval: Q23, Q25, Q29
- PDF answer questions: Q1, Q16, Q17
- spreadsheet answer questions: Q2, Q3, Q4, Q5, Q9, Q10, Q12, Q15, Q22, Q30
- hybrid spreadsheet + PDF questions: Q23, Q28

---

## 4. Expected Retrieval Behavior by Query Type

### Policy or narrative questions

- prefer semantic retrieval over PDF sections
- use exact search only for concept terms or document names
- final answer may require a contextual narrative explanation

### Exact lookup questions

- prefer exact matching against report metadata, codes, and row labels
- use structured retrieval if the result is a numeric status row

### Table and numeric questions

- prefer structured query first
- use exact search to align the geography and metric
- use semantic retrieval only for explanatory context

### Version and duplicate questions

- metadata comparison and hash analysis before retrieval
- historical version handling must be explicit

### Cross-document comparison questions

- run multiple retrieval branches, fuse results, and compare with a common geography or time dimension

---

## 5. Validation Criteria for the RAG System

The final implementation should be evaluated against this set by checking:

- answer correctness
- correct source file and table/row
- correct retrieval mode used
- numeric correctness
- version selection correctness
- policy context fidelity
- citation accuracy

---

## 6. Summary

This evaluation set is not synthetic or generic. It is grounded in the actual families and structures found in the corpus. It captures the dominant query patterns that the final RAG system must handle with a hybrid retrieval strategy.

## Phase 2 Corpus-Derived Dataset

The executable evaluation dataset is [artifacts/query_evaluation_cases.json](artifacts/query_evaluation_cases.json). It contains 40 cases with expected source filenames, required filters, retrieval flags, provenance requirements, and notes about evidence limitations. The cases were checked against the approved 45-file manifest and representative report structures.

The dataset explicitly covers the excluded corrupted source as an audit/provenance case only. It must never be an expected production data source, structured record source, embedding source, or index candidate.
