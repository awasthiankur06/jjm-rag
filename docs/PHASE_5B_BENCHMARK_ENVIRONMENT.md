# Phase 5B Benchmark Environment

## Current status

The benchmark tooling is prepared, but the heavyweight experiments are environment-blocked. The final gate is:

`PHASE_5B_READY_FOR_BENCHMARK_EXECUTION`

This means the tooling is ready and remaining blockers are environmental. It does not mean the remaining benchmarks have passed.

## Observed environment

Recorded in [artifacts/phase5b_environment_probe.json](../artifacts/phase5b_environment_probe.json):

- Windows 10 build `10.0.26200`, AMD64
- Python 3.11.6 in `.venv`
- 12 logical CPUs
- 7.72 GiB physical RAM; approximately 1.59 GiB available at probe time
- Workspace disk: approximately 956 GiB free
- NVIDIA GPU/CUDA: unavailable
- Docker and Docker Compose: unavailable
- PostgreSQL client/server tools: unavailable
- DNS resolution for `api.x.ai`: available
- `uv`: available; `pip` command was not discoverable directly
- BGE-M3, E5, PostgreSQL, pgvector, xAI, framework, and reranker Python packages: unavailable
- `XAI_API_KEY`: unavailable

RAM availability is too low for a comfortable local BGE-M3 or E5-large run without closing applications or using an approved isolated machine. No model was downloaded automatically.

## Isolated environments

Requirements are deliberately outside the project dependency files:

- `benchmarks/requirements-embeddings.txt`
- `benchmarks/requirements-pgvector.txt`
- `benchmarks/requirements-xai.txt`
- `benchmarks/requirements-frameworks.txt`
- `benchmarks/requirements-reranker.txt`

Use a separate virtual environment for each benchmark family. Example with `uv`:

```powershell
uv venv .benchmarks\embeddings\.venv
.\.benchmarks\embeddings\.venv\Scripts\python.exe -m pip install -r benchmarks\requirements-embeddings.txt
```

Do not install these packages into `.venv` used by the validated retrieval tests.

## Prerequisites by benchmark

### Embeddings

Required:

- isolated Python environment;
- PyTorch, Transformers, FlagEmbedding, Sentence Transformers, NumPy;
- local model files or explicit approval to download models;
- preferably 16 GiB or more RAM for CPU experiments, or an approved CUDA GPU with compatible drivers;
- enough model-cache disk space.

The runner requires local model paths by default. `--allow-download` is an explicit opt-in and should only be used in an approved environment.

### PostgreSQL + pgvector

Required:

- PostgreSQL 15+ or an approved compatible version;
- `psycopg` and `pgvector` in the isolated benchmark environment;
- `vector` extension installed;
- a disposable local database and DSN supplied through `PGVECTOR_DSN`;
- permission to create/drop an isolated schema.

Docker is unavailable in the current environment. A native PostgreSQL install or approved PostgreSQL host is required. The benchmark must use only the representative semantic subset and must not connect to a production database.

### Grok/xAI

Required:

- approved `XAI_API_KEY` environment variable;
- `openai` package in the isolated xAI environment;
- approved data-transfer, retention, region, and security policy;
- network access to `https://api.x.ai/v1`;
- model, timeout, retry, token-budget, and cost ceilings.

The runner sends trimmed evidence only. It never sends the complete corpus and never writes the key to an artifact.

### Frameworks

Install each framework in a separate environment using `benchmarks/requirements-frameworks.txt`. No framework package is required for the validated application. Missing packages produce explicit blocked results.

### Reranker

Required only for an optional follow-up:

- local cross-encoder model and Sentence Transformers/PyTorch runtime;
- approved model files and enough RAM/GPU;
- no automatic download.

The current decision remains `NOT_JUSTIFIED`.

## Exact commands

Run all prepared benchmarks:

```powershell
.\.venv\Scripts\python.exe benchmarks\run_all.py
```

Embedding benchmark after isolated model setup:

```powershell
.\.benchmarks\embeddings\.venv\Scripts\python.exe benchmarks\run_embedding_benchmark.py --bge-path D:\models\bge-m3 --e5-path D:\models\multilingual-e5-large
```

PostgreSQL benchmark after isolated database setup:

```powershell
$env:PGVECTOR_DSN = 'postgresql://<approved-user>:<approved-password>@<host>:<port>/<database>'
.\.benchmarks\pgvector\.venv\Scripts\python.exe benchmarks\run_pgvector_benchmark.py
```

Grok benchmark after security approval and secret injection:

```powershell
$env:XAI_API_KEY = '<type securely in the terminal; do not place in files>'
.\.benchmarks\xai\.venv\Scripts\python.exe benchmarks\run_grok_benchmark.py
```

Do not include credentials in shell history where policy forbids it. Prefer the deployment secret manager for real execution.

## Security boundary

No external corpus upload occurred in this phase. The excluded corrupted source is never included in semantic candidates or evidence packages. Any xAI execution requires explicit approval for sending selected source excerpts and provenance metadata outside the local environment.
