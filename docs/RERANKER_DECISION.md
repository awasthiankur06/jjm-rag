# Reranker Decision

## Decision

`NOT_JUSTIFIED`

The validated post-remediation baseline without a reranker has:

- Recall@1: 0.4957264957264957
- Recall@3: 0.8653846153846154
- Recall@5: 0.9423076923076923
- Recall@10: 1.0
- hybrid retrieval accuracy: 1.0

No reranker package or model is installed, so no reranker run was fabricated. The machine-readable result is [artifacts/reranker_benchmark.json](../artifacts/reranker_benchmark.json).

Recall@1 indicates that a later top-1 quality experiment could be useful, but the current evidence does not establish that a cross-encoder would improve useful evidence ordering enough to justify additional latency, model serving, and operational complexity. The trigger for that experiment is a JJM-specific answer-quality benchmark focused on top-1/top-3 evidence ordering.
