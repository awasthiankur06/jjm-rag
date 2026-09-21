# Architecture

This repository implements the approved hybrid RAG architecture for the JJM corpus.

## Core principles

- semantic retrieval for policy and explanatory content
- exact retrieval for identifiers, names, and codes
- structured retrieval for table metrics and comparisons
- provenance-aware citations and row/table traceability
- version-aware handling for duplicate and revision files
- deterministic processing outside the LLM

## Layered design

1. Ingestion
2. Extraction and parser selection
3. Normalization and canonical representation
4. Metadata and version tracking
5. Structured storage
6. Searchable text representation
7. Exact search and semantic retrieval
8. Query routing and hybrid retrieval
9. Grok/xAI synthesis and citation validation
10. Evaluation and observability

## Notes

This file is intentionally concise because the detailed design baseline is in `RAG_ARCHITECTURE_DESIGN.md`.
