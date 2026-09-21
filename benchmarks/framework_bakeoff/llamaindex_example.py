"""Isolated LlamaIndex metadata/provenance spike."""
try:
    from llama_index.core import Document, VectorStoreIndex
except ImportError as exc:
    raise SystemExit(f"BLOCKED_BY_MISSING_LLAMAINDEX: {exc}")

# Any adapter must preserve source hash, source status, and page/table/row metadata.
print("LlamaIndex spike prerequisites available; measure metadata and provenance propagation here.")
