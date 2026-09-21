# JJM RAG

This project is an implementation foundation for a hybrid retrieval-augmented generation system over the Jal Jeevan Mission (JJM) corpus.

## Design baseline

The implementation follows the approved design in:

- `RAG_ARCHITECTURE_DESIGN.md`
- `RAG_QUERY_EVALUATION.md`

## Project structure

- `jjm_rag/ingestion` — file discovery, detection, parsing, version tracking
- `jjm_rag/parsing` — parser implementations for PDF and HTML-exported table sources
- `jjm_rag/normalization` — canonical conversion
- `jjm_rag/structured_storage` — database schema and structured record handling
- `jjm_rag/text` — chunking and searchable text representation
- `jjm_rag/indexing` — vector and keyword index abstractions
- `jjm_rag/retrieval` — exact, structured, and semantic retrieval
- `jjm_rag/query_routing` — intent classification and strategy selection
- `jjm_rag/xai_integration` — Grok/xAI integration layer
- `jjm_rag/citation` — provenance and citation management
- `jjm_rag/evaluation` — evaluation harness for the JJM query set
- `jjm_rag/observability` — logging and tracing

## Quick start

1. Create a virtual environment.
2. Install dependencies with `pip install -r requirements.txt`.
3. Run `pytest -q`.
4. Start implementing the ingestion pipeline from the modules in `jjm_rag/ingestion`.

## Current status

This repository is in the Phase 1 implementation milestone: ingestion and extraction foundation.
