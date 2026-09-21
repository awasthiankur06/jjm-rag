from __future__ import annotations

from pathlib import Path


class ExactSearchIndex:
    """Simple exact/keyword index for names, codes, report titles and identifiers."""

    def __init__(self):
        self.entries: dict[str, list[str]] = {}

    def index_files(self, paths: list[Path]) -> None:
        for path in paths:
            self.entries.setdefault(path.name.lower(), []).append(str(path))

    def search(self, query: str) -> list[str]:
        q = query.lower().strip()
        if not q:
            return []
        return self.entries.get(q, [])

    def search_partial(self, query: str, limit: int = 10) -> list[str]:
        q = query.lower().strip()
        if not q:
            return []
        matches = []
        for key, values in self.entries.items():
            if q in key:
                matches.extend(values)
        return matches[:limit]
