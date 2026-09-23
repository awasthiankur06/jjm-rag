# Qdrant transfer snapshot

This directory contains a GitHub-safe split export of the validated local Qdrant snapshot. It is derived from the PostgreSQL canonical corpus included in the parent transfer directory.

Source collection:

- Qdrant version: `1.18.2`
- Collection: `jjm_rag_semantic_gemini_embedding_001_v2_header_repair`
- Point count: `545`
- Original snapshot SHA-256: `91c0a909d978d6b80aa39f2537714f30673958a70460d109075f79c1ca0fecdc`

On RHEL, reassemble and validate before importing:

```bash
cd /opt/installers/jjm-rag/deployment/rhel7/transfer/qdrant
bash assemble-qdrant-snapshot.sh
```

The script will not overwrite an existing snapshot. Do not import this snapshot into a Qdrant collection unless its PostgreSQL canonical IDs and text are confirmed to match the restored database.
