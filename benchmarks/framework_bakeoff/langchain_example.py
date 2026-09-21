"""Isolated LangChain spike; does not modify the validated application."""
try:
    from langchain_core.documents import Document
    from langchain_core.retrievers import BaseRetriever
    from langchain_core.tools import StructuredTool
except ImportError as exc:
    raise SystemExit(f"BLOCKED_BY_MISSING_LANGCHAIN: {exc}")

# Define only a small adapter here after installing the isolated requirements.
# The adapter must carry source_id, filename, sha256, and location in metadata.
print("LangChain spike prerequisites available; implement adapter measurement here.")
