# Parser header repair validation

## Defects fixed

The legacy HTML table parser treated leading `<th>` body rows as headers.  In
`CS1 A. Coverage.xls`, this promoted the total-row values `641995` and
`377791` into metric headers.  It also discarded the real `State/ UT` header,
which prevented geography dimensions from being created.

`Format D5- List of Sanction Order.xls` contains a second ordinal column
legend (`1` through `8`) in its HTML export and duplicate visual header cells
after the real data columns.  Those labels could become phantom numeric
metrics.

The parser now:

- only uses the leading header block;
- stops before numeric body/total rows;
- consumes ordinal-only legend rows without treating them as facts;
- removes trailing columns with no real `<td>` data;
- retains geography headers such as `State/ UT`; and
- never uses numeric-only header text as a metric name.

## Live disposable PostgreSQL validation

The confirmed disposable database was rebuilt from the unchanged production
manifest.  Results were 44 eligible sources ingested, 1 corrupted source
excluded, and 0 ingestion failures.  The final canonical counts were:

- documents: 44
- structured records and observations: 33,033 each
- canonical content units: 3,466
- provenance records: 36,499

`CS1 A. Coverage.xls` now has 35 geography dimensions.  PostgreSQL has zero
numeric-only metric names, including zero for the D5 source; the excluded
corrupted workbook has zero document records.  A repeat ingestion left the
logical entity counts unchanged.

## Validation limits

`pytest -q` passed 109 tests with 2 third-party deprecation warnings.  The
live, deterministic 40-case PostgreSQL evaluation is in
`artifacts/post_header_repair_postgres_evaluation.json`.  Its retrieval
metrics are evidence of the current system, not a claim of complete RAG
readiness: Recall@10 is 0.9508547008547009, provenance accuracy is 0.975,
structured retrieval accuracy is 0.4, and cross-document accuracy is 0.5.
