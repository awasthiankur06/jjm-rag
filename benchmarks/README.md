# Phase 5B Benchmark Tooling

This directory contains isolated runners and environment definitions. They do not modify the validated retrieval architecture or install dependencies into the project environment.

## Entry point

```powershell
.\.venv\Scripts\python.exe benchmarks\run_all.py
```

The command writes `artifacts/phase5b_run_all.json` and invokes each runner independently. Missing prerequisites produce explicit `BLOCKED` statuses.

## Runners

- `run_embedding_benchmark.py`: BGE-M3 versus multilingual-e5-large on the JJM semantic dataset.
- `run_pgvector_benchmark.py`: disposable PostgreSQL + pgvector mechanics benchmark.
- `run_grok_benchmark.py`: controlled xAI evidence-grounding benchmark using `XAI_API_KEY`.
- `run_reranker_benchmark.py`: optional cross-encoder comparison; no automatic model download.
- `framework_bakeoff/`: independent custom, LangChain, LangGraph, and LlamaIndex spikes.

See `docs/PHASE_5B_BENCHMARK_ENVIRONMENT.md` for isolated installation and security prerequisites.
