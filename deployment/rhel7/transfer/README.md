# PostgreSQL transfer archive

`jjm_rag_canonical_pg18.dump` is a PostgreSQL 18 custom-format export of the validated local V1 canonical corpus, created on 2026-09-23.

Before restore, validate it from the target directory:

```bash
sha256sum -c jjm_rag_canonical_pg18.dump.sha256
```

Restore only with PostgreSQL 18 or newer client tools into an approved empty database. The archive does not contain database credentials, API keys, or tokens. It contains the corpus-derived canonical data and provenance, and is intentionally included in this public repository at the repository owner's direction.

The Qdrant snapshot is not included here. Qdrant remains a derived index and must be either imported only after alignment verification or rebuilt from this PostgreSQL corpus.
