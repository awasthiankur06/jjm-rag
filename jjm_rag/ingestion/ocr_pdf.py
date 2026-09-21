import argparse
import hashlib
import json
import os
import statistics
import time
from datetime import datetime, timezone

import fitz
import pytesseract
from PIL import Image


TESSERACT_PATH = r"C:\Tesseract-OCR\tesseract.exe"


def sha256_file(path):
    digest = hashlib.sha256()
    with open(path, "rb") as source:
        for chunk in iter(lambda: source.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def percentile(values, fraction):
    if not values:
        return None
    ordered = sorted(values)
    index = min(len(ordered) - 1, round((len(ordered) - 1) * fraction))
    return ordered[index]


def summarize_pages(pages):
    char_counts = [page["character_count"] for page in pages]
    word_counts = [page["word_count"] for page in pages]
    confidence_values = [
        page["confidence"]["mean"]
        for page in pages
        if page.get("confidence", {}).get("mean") is not None
    ]
    empty_threshold = 20
    suspicious = [
        {
            "page_number": page["page_number"],
            "character_count": page["character_count"],
            "word_count": page["word_count"],
            "confidence_mean": page.get("confidence", {}).get("mean"),
            "reason": "near_empty_text",
        }
        for page in pages
        if page["status"] != "success"
        or page["character_count"] <= empty_threshold
        or (
            page.get("confidence", {}).get("mean") is not None
            and page["character_count"] > empty_threshold
            and page["confidence"]["mean"] < 35
        )
    ]
    return {
        "total_pages": len(pages),
        "rendered_pages": sum(page["rendered"] for page in pages),
        "ocr_success_pages": sum(page["status"] == "success" for page in pages),
        "failed_pages": sum(page["status"] == "failed" for page in pages),
        "empty_or_near_empty_pages": sum(
            page["character_count"] <= empty_threshold for page in pages
        ),
        "character_count": {
            "total": sum(char_counts),
            "minimum": min(char_counts) if char_counts else 0,
            "maximum": max(char_counts) if char_counts else 0,
            "median": statistics.median(char_counts) if char_counts else 0,
            "mean": statistics.mean(char_counts) if char_counts else 0,
        },
        "word_count": {
            "total": sum(word_counts),
            "minimum": min(word_counts) if word_counts else 0,
            "maximum": max(word_counts) if word_counts else 0,
            "median": statistics.median(word_counts) if word_counts else 0,
            "mean": statistics.mean(word_counts) if word_counts else 0,
        },
        "confidence": {
            "pages_with_confidence": len(confidence_values),
            "minimum": min(confidence_values) if confidence_values else None,
            "maximum": max(confidence_values) if confidence_values else None,
            "median": statistics.median(confidence_values) if confidence_values else None,
            "mean": statistics.mean(confidence_values) if confidence_values else None,
        },
        "suspicious_pages": suspicious,
    }


def representative_pages(pages):
    if not pages:
        return []
    indexes = sorted({0, len(pages) // 4, len(pages) // 2, (3 * len(pages)) // 4, len(pages) - 1})
    return [
        {
            "page_number": pages[index]["page_number"],
            "character_count": pages[index]["character_count"],
            "word_count": pages[index]["word_count"],
            "status": pages[index]["status"],
            "confidence": pages[index].get("confidence", {}),
            "text_sample": pages[index]["text"][:500],
        }
        for index in indexes
    ]


def run_ocr(pdf_path, output_path, dpi=200):
    if not os.path.isfile(TESSERACT_PATH):
        raise FileNotFoundError(f"Tesseract executable not found: {TESSERACT_PATH}")
    pytesseract.pytesseract.tesseract_cmd = TESSERACT_PATH
    source_sha256 = sha256_file(pdf_path)
    tesseract_version = str(pytesseract.get_tesseract_version())
    pages = []
    started = time.time()

    with fitz.open(pdf_path) as document:
        expected_pages = len(document)
        for page_index in range(expected_pages):
            page_number = page_index + 1
            entry = {
                "source_filename": os.path.basename(pdf_path),
                "source_sha256": source_sha256,
                "page_number": page_number,
                "source_page_index": page_index,
                "rendered": False,
                "rendering": {"method": "PyMuPDF get_pixmap", "dpi": dpi},
                "text": "",
                "character_count": 0,
                "word_count": 0,
                "confidence": {"mean": None, "minimum": None, "maximum": None, "word_count": 0},
                "ocr_engine": "Tesseract",
                "ocr_engine_version": tesseract_version,
                "status": "failed",
                "error": None,
            }
            try:
                page = document.load_page(page_index)
                pixmap = page.get_pixmap(dpi=dpi, alpha=False)
                entry["rendered"] = True
                image = Image.frombytes("RGB", [pixmap.width, pixmap.height], pixmap.samples)
                data = pytesseract.image_to_data(
                    image,
                    output_type=pytesseract.Output.DICT,
                    config="--psm 6",
                    lang="eng",
                )
                text = pytesseract.image_to_string(image, config="--psm 6", lang="eng")
                confidences = []
                for raw_confidence, raw_text in zip(data["conf"], data["text"]):
                    if raw_text.strip():
                        try:
                            confidence = float(raw_confidence)
                        except (TypeError, ValueError):
                            continue
                        if confidence >= 0:
                            confidences.append(confidence)
                entry["text"] = text.strip()
                entry["character_count"] = len(entry["text"])
                entry["word_count"] = len(entry["text"].split())
                entry["confidence"] = {
                    "mean": statistics.mean(confidences) if confidences else None,
                    "minimum": min(confidences) if confidences else None,
                    "maximum": max(confidences) if confidences else None,
                    "word_count": len(confidences),
                }
                entry["status"] = "success"
            except Exception as error:
                entry["error"] = repr(error)
            pages.append(entry)
            print(f"page {page_number}/{expected_pages}: {entry['status']} ({entry['character_count']} chars)", flush=True)

    result = {
        "artifact_type": "page_level_ocr",
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "source_filename": os.path.basename(pdf_path),
        "source_path": os.path.abspath(pdf_path),
        "source_sha256": source_sha256,
        "pdf_page_count": len(pages),
        "ocr_engine": "Tesseract",
        "ocr_engine_version": tesseract_version,
        "pytesseract_version": pytesseract.__version__,
        "pymupdf_version": fitz.VersionBind,
        "pillow_version": Image.__version__,
        "rendering": {"method": "PyMuPDF get_pixmap", "dpi": dpi, "color": "RGB", "alpha": False},
        "ocr_config": {"language": "eng", "psm": 6},
        "elapsed_seconds": round(time.time() - started, 2),
        "summary": summarize_pages(pages),
        "representative_pages": representative_pages(pages),
        "pages": pages,
    }
    os.makedirs(os.path.dirname(output_path), exist_ok=True)
    with open(output_path, "w", encoding="utf-8") as artifact:
        json.dump(result, artifact, indent=2, ensure_ascii=False)
    return result


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--pdf", required=True)
    parser.add_argument("--output", required=True)
    parser.add_argument("--dpi", type=int, default=200)
    args = parser.parse_args()
    run_ocr(args.pdf, args.output, args.dpi)
