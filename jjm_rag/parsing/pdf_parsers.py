from __future__ import annotations

import json
from pathlib import Path

from PyPDF2 import PdfReader

from jjm_rag.models.canonical import Document, Provenance, Section, SourceMetadata


class PdfParser:
    parser_name = "pdf_parser"

    def parse(self, path: Path, family: str = "unknown", ocr_artifact: str | None = None) -> Document:
        pages: list[dict] = []
        if ocr_artifact and Path(ocr_artifact).exists():
            artifact = json.loads(Path(ocr_artifact).read_text(encoding="utf-8"))
            pages = [{"page_number": page["page_number"], "text": page.get("text", "").replace("\x00", "")} for page in artifact.get("pages", [])]
        else:
            reader = PdfReader(str(path))
            for index, page in enumerate(reader.pages, start=1):
                pages.append({"page_number": index, "text": (page.extract_text() or "").replace("\x00", "")})

        sections = [
            Section(
                section_id=f"{path.stem}-page-{page['page_number']}",
                title=f"Page {page['page_number']}",
                text=page["text"],
                page_numbers=[page["page_number"]],
                provenance=Provenance(
                    document_id=path.stem,
                    source_path=str(path),
                    page_numbers=[page["page_number"]],
                    section_path=f"Page {page['page_number']}",
                ),
            )
            for page in pages
        ]
        metadata = SourceMetadata(
            source_path=str(path),
            filename=path.name,
            file_size=path.stat().st_size,
            detected_format="pdf",
            parser_name=self.parser_name,
        )
        return Document(
            document_id=path.stem,
            source_path=str(path),
            source_metadata=metadata,
            family=family,
            sections=sections,
            text_chunks=[page["text"] for page in pages if page["text"].strip()],
        )
