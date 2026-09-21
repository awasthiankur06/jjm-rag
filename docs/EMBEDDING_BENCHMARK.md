# Embedding Benchmark

## Result

`BENCHMARK_INCONCLUSIVE`

A representative semantic dataset was created at [artifacts/semantic_benchmark_dataset.json](../artifacts/semantic_benchmark_dataset.json) from actual JJM policy, OCR-derived PDF, report-description, format, government-terminology, and state/district metadata units. Raw numeric rows were excluded from semantic scoring.

The dataset contains 8 representative query cases. The existing validated lexical semantic proxy reports a 0.5 semantic source hit rate, but that is a reference point, not a BGE-M3 or multilingual-e5-large result.

## Execution status

Both required models were blocked in the selected Python 3.11.6 environment:

- `BAAI/bge-m3`: blocked because `torch`, `transformers`, `FlagEmbedding`, and `sentence-transformers` are not installed.
- `intfloat/multilingual-e5-large`: blocked because `torch`, `transformers`, and `sentence-transformers` are not installed.

No model downloads or external inference calls were attempted. No model result is fabricated.

## Candidate facts

| Model | Documented dimensions | Documented limit | Fit | Decision |
|---|---:|---:|---|---|
| BGE-M3 | 1024 | 8192 tokens | Multilingual dense, sparse, and multi-vector modes; attractive for policy/OCR and hybrid retrieval | SHORTLISTED |
| multilingual-e5-large | 1024 | 512 tokens | Multilingual query/passage retrieval with explicit prefixes | SHORTLISTED |

## Required next run

Run both models with pinned revisions and identical preprocessing. Measure Recall@1, @3, @5, @10, MRR, embedding latency, throughput, peak memory, model size, reproducibility across repeated runs, and deployment complexity. Evaluate semantic cases only, not exact identifiers or numeric rows.

The selected model must improve semantic evidence ordering without replacing exact or structured retrieval. This phase cannot choose between the two candidates.
