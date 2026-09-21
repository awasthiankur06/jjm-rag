from __future__ import annotations

import hashlib
from pathlib import Path


def compute_content_hash(path: str | Path) -> str:
    """Return a stable SHA-256 hash for file content."""
    file_path = Path(path)
    digest = hashlib.sha256()
    with file_path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(65536), b""):
            digest.update(chunk)
    return digest.hexdigest()


def classify_content_relationship(path_a: str | Path, path_b: str | Path) -> str:
    """Compare actual content and classify likely relationship between two files."""
    a = Path(path_a)
    b = Path(path_b)
    if a == b:
        return "identical"

    hash_a = compute_content_hash(a)
    hash_b = compute_content_hash(b)
    if hash_a == hash_b:
        return "identical"

    if a.suffix.lower() == b.suffix.lower():
        return "same-structure-different-data"

    return "unknown"
