# Multi-level table headers and geography reconciliation

## What was repaired

Some legacy HTML-exported Excel reports store the geography as an exact `State Name` column and their measurements under multi-level headings. The canonical parser retained those values and every header path, but the older geography recognizer did not treat `State Name` as a dimension. Consequently, all metrics from that row could be present without a state link.

The production parser now recognizes exact standalone source labels `State`, `State Name`, `State/UT`, and `State Union Territory`. It deliberately does not use substring matching and will not mistake headings such as `State Referral Lab` or a nested metric leaf named `State` for geography.

Existing canonical PostgreSQL rows were reconciled transactionally by their existing document, table, and source-row identity. No documents, raw source values, canonical text, provenance identifiers, or Qdrant point identities were deleted or recreated.

## Multi-level clarification behavior

If a report and geography resolve to several nested source fields, the application does not select the first returned value. It asks the user to choose from the actual persisted header paths. For example, the J5 report offers paths such as:

- `PWS Habitations → With FHTC Coverage >=100 % → House Connectons`
- `PWS Habitations → With FHTC Coverage >=75 and <100 % → House Holds`
- `Total Habitations as on 01/04/2026`

The selected full path is applied as an exact normalized header-path filter before a structured fact is chosen. A repeated leaf such as `House Holds` alone is never treated as a unique metric.

This is generic for every parsed structured table. PDFs that have deterministic table/header extraction use the same behavior. PDFs represented only as page or section text retain their source/page provenance but are not falsely advertised as structured columns.

## Verified example

For `Habitation wise FHTC Coverage (Reported Till 23/08/2026)` and Karnataka:

- an ambiguous request asks for a metric/header choice;
- selecting `PWS Habitations → With FHTC Coverage >=100 % → House Connectons` returns raw value `6990630` from source cell `R18C22`;
- requesting `Total Habitations as on 01/04/2026` returns `57879`.

The detailed live reconciliation outcome is recorded in [multiheader_geography_reconciliation.json](../artifacts/multiheader_geography_reconciliation.json).
