from __future__ import annotations

from pathlib import Path

SUPPORTED_SUFFIXES = {".xls", ".xlsx", ".csv", ".pdf", ".html", ".htm"}


def discover_files(root: str | Path, recursive: bool = True) -> list[Path]:
    """Discover candidate corpus files while ignoring directories and unrelated file types."""
    root_path = Path(root)
    if not root_path.exists():
        raise FileNotFoundError(f"Input directory does not exist: {root_path}")

    files: list[Path] = []
    candidates = root_path.rglob("*") if recursive else root_path.iterdir()
    for candidate in candidates:
        if candidate.is_file() and candidate.suffix.lower() in SUPPORTED_SUFFIXES:
            files.append(candidate)

    return sorted(files)
