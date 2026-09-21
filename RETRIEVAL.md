# Retrieval

The retrieval design follows the approved hybrid RAG architecture.

## Retrieval modes

- semantic retrieval for policy and explanatory sections
- exact retrieval for names, codes, references, and format identifiers
- structured retrieval for metrics, counts, comparisons, and geography filters
- hybrid retrieval for combination questions

## Retrieval principles

- deterministic operations remain outside the LLM
- exact search is independent of semantic similarity
- structured queries are validated before execution
- retrieved content is mapped back to the canonical source representation for citations
