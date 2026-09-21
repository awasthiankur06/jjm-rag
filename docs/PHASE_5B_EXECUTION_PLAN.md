# Phase 5B Execution Plan

## Current gate

`PHASE_5B_READY_FOR_BENCHMARK_EXECUTION`

The tooling is prepared. The current machine lacks the dependencies and services needed for the remaining live benchmarks.

## Sequence

1. Preserve and verify [artifacts/phase5b_baseline_identity.json](../artifacts/phase5b_baseline_identity.json).
2. Provision separate isolated environments from the benchmark requirement files.
3. Prepare an approved CPU/GPU environment and local model paths.
4. Run `benchmarks/run_embedding_benchmark.py` for BGE-M3 and multilingual-e5-large.
5. Provision a disposable PostgreSQL instance with pgvector, set `PGVECTOR_DSN`, and run `benchmarks/run_pgvector_benchmark.py`.
6. Obtain security approval for evidence transfer and inject `XAI_API_KEY` through the approved secret path.
7. Run `benchmarks/run_grok_benchmark.py` with the minimum retrieved evidence only.
8. Install framework packages in an isolated environment and run the examples under `benchmarks/framework_bakeoff/`.
9. If product requirements justify it, provision one approved local reranker model and run `benchmarks/run_reranker_benchmark.py`.
10. Run `benchmarks/run_all.py` and inspect each runtime artifact separately.
11. Run `pytest -q` and reverify retrieval/corpus hashes.
12. Update technology decisions only from executed measurements.

## Required interpretation rules

- `EXECUTED` means the runner completed and persisted raw/derived measurements.
- `BLOCKED` means an explicit prerequisite was unavailable.
- `NOT_RUN` means the benchmark was intentionally not attempted.
- Blocked or not-run measurements must never be converted into passing results.
- Synthetic diagnostic vectors, if used for database mechanics, must not be interpreted as semantic quality.
- Current-corpus latency must not be extrapolated to untested scale.
- The existing 40-case retrieval benchmark and source ground truth must remain untouched.

## Exit criteria

The next phase can update the technology gate only after:

- both embedding candidates have comparable JJM semantic measurements;
- pgvector has local insertion, filtering, provenance, and latency measurements;
- Grok has grounded-generation, citation, numeric, abstention, latency, token, and cost measurements;
- framework value is assessed in an installed isolated environment or explicitly rejected for a documented reason;
- all existing tests and baseline hash checks pass.

No production chatbot or API implementation belongs in this phase.
