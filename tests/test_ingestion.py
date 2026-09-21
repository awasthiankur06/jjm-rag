import hashlib
import tempfile
from pathlib import Path

from jjm_rag.ingestion.discovery import discover_files
from jjm_rag.ingestion.format_detection import detect_format
from jjm_rag.ingestion.versioning import compute_content_hash, classify_content_relationship


def test_detect_html_like_xls_file():
    with tempfile.TemporaryDirectory() as tmp:
        path = Path(tmp) / "report.xls"
        path.write_text(
            "<html><body><table><tr><td>State</td><td>Coverage</td></tr></table></body></html>",
            encoding="utf-8",
        )
        detected = detect_format(path)
        assert detected.format_name == "html_table"


def test_detect_pdf_file():
    with tempfile.TemporaryDirectory() as tmp:
        path = Path(tmp) / "guidance.pdf"
        path.write_bytes(b"%PDF-1.4\n1 0 obj\n<<>>\nendobj\n")
        detected = detect_format(path)
        assert detected.format_name == "pdf"


def test_content_hash_and_relationship_detection():
    with tempfile.TemporaryDirectory() as tmp:
        p1 = Path(tmp) / "report.xls"
        p2 = Path(tmp) / "report (1).xls"
        payload = b"state,coverage\nAssam,90\n"
        p1.write_bytes(payload)
        p2.write_bytes(payload)

        h1 = compute_content_hash(p1)
        h2 = compute_content_hash(p2)
        assert h1 == h2
        assert classify_content_relationship(p1, p2) == "identical"


def test_discover_files_filters_non_files():
    with tempfile.TemporaryDirectory() as tmp:
        root = Path(tmp)
        (root / "a.xls").write_text("x", encoding="utf-8")
        (root / "b.txt").write_text("y", encoding="utf-8")
        (root / "sub").mkdir()
        (root / "sub" / "c.xls").write_text("z", encoding="utf-8")

        files = discover_files(root)
        names = {p.name for p in files}
        assert names == {"a.xls", "c.xls"}
