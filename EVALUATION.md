# Evaluation

The evaluation baseline is the approved query matrix in `RAG_QUERY_EVALUATION.md`.

## Metrics

- retrieval accuracy
- answer accuracy
- numeric accuracy
- citation correctness
- source correctness
- latency
- token/model usage
- failure rate

## Minimum regression set

- policy definition question
- state coverage lookup
- district status question
- sanction reference lookup
- version comparison question
- hybrid coverage + policy question

## Execution model

Evaluation must run after each milestone to ensure the ingestion and retrieval pipeline remains faithful to the real corpus and approved design.
