# Source-family consolidation

## Purpose

The raw Excel and PDF files are immutable evidence. The application reduces
query complexity by treating compatible source members as one logical report
family in PostgreSQL, while retaining the exact source file and cell/page
provenance for every returned fact.

No raw source is physically merged, renamed, or deleted by this process.

## Reconciliation contract

Repeated source-derived titles are compared using canonical PostgreSQL rows:

- source SHA-256 and format code;
- complete source-derived header-path set;
- state/district row-key coverage;
- value conflicts for the same geography/header key.

The audit returns one of these decisions:

| Decision | Meaning | Retrieval behavior |
| --- | --- | --- |
| `LOGICALLY_CONSOLIDATE_ROWS_KEEP_RAW_SOURCES` | Same schema and non-overlapping geographic partitions. | Treat the member rows as one logical report family; retain physical source provenance. |
| `REVIEW_POTENTIAL_DUPLICATES_KEEP_RAW_SOURCES` | Same geographic scope and values need an explicit duplicate review. | Do not remove either source automatically. |
| `KEEP_SEPARATE_CONFLICTING_SNAPSHOTS` | Same geography/header contains conflicting values. | Keep distinct sources; ask for report/snapshot selection when needed. |
| `KEEP_SEPARATE_PENDING_METADATA_OR_SCHEMA_REVIEW` | Schema or geographic identity is insufficient for a safe merge. | Do not combine results automatically. |

Filename suffixes such as `(1)`, `(2)`, and `(3)` are never version evidence.

## V1 live PostgreSQL result after selected-state repair

`artifacts/source_family_reconciliation_v2_pm4_repaired.json` records the
latest live audit. The original V1 artifact is retained as the pre-repair
baseline.

| Repeated-title family | Decision | Reason |
| --- | --- | --- |
| District-wise rural population (B11) | Logical consolidation | Compatible schema; members are non-overlapping district partitions. |
| Quality-affected habitations and population (C17) | Logical consolidation | Compatible schema; members are non-overlapping district partitions. |
| Status of pipe water supply in school (F26) | Logical consolidation | Compatible schema; members are non-overlapping district partitions. |
| Beneficiary verification (J6) | Logical consolidation | Compatible schema; members are non-overlapping district partitions. |
| Progress tracker of verification schemes (PM4) | Logical consolidation | The source-derived `State:` parameter is now attached to every division row; members are non-overlapping state partitions. |

These decisions consolidate the query view only. They do not claim that one
physical file supersedes another.

## Running the audit

The audit requires the environment-provided `JJM_DATABASE_URL` and refuses to
fall back to SQLite or an unspecified database:

```powershell
.venv\Scripts\python.exe -m jjm_rag.evaluation.source_family_reconciliation `
  --output artifacts/source_family_reconciliation_v1.json
```

Review the generated artifact before changing any source-retention policy. The
ingestion CLI additionally blocks an eligible duplicate SHA-256 before writing
to the database and retains same-title variants for this reconciliation rather
than silently combining them.
