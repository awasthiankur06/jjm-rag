from __future__ import annotations

from abc import ABC, abstractmethod
from pathlib import Path

from jjm_rag.models.canonical import Document


class BaseParser(ABC):
    """Base parsing contract for corpus documents."""

    parser_name: str = "base"

    @abstractmethod
    def parse(self, path: Path, family: str = "unknown") -> Document:
        raise NotImplementedError
