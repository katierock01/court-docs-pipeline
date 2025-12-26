"""
OCR extraction pipeline for court documents.

Phase 1 workflow:
- Read PDFs from an input directory (default: court_docs/).
- Use pdf2image + pytesseract to OCR each page.
- Write raw text files to an output directory with the same basename.
- Log errors and flag pages with low confidence for manual review.
- Generate visual progress feedback and quality metrics.

Requirements:
- Python 3.8+
- pip install pytesseract pdf2image pillow tqdm
- Local Tesseract installation accessible on PATH (or configure tesseract_cmd)
- Poppler binaries available to pdf2image (pass --poppler-path if needed)
"""

import argparse
import logging
import sys
import csv
import json
import time
import os
from dataclasses import dataclass
from pathlib import Path
from typing import List, Optional, Tuple
from datetime import datetime

# Optional imports are runtime-only; suppress static analysis warnings for missing modules.
try:
    from pdf2image import convert_from_path  # pyright: ignore[reportMissingImports]
    from PIL import Image  # pyright: ignore[reportMissingImports]
    import pytesseract  # pyright: ignore[reportMissingImports]
    from tqdm import tqdm  # pyright: ignore[reportMissingImports]
except ImportError as exc:  # pragma: no cover - import guard only
    missing = (
        "Missing dependency. Install with: pip install pytesseract pdf2image pillow tqdm\n"
        f"Original error: {exc}"
    )
    raise SystemExit(missing)

# ---------------------------------------------------------------------------
# Configuration
# ---------------------------------------------------------------------------

DEFAULT_INPUT_DIR = Path("court_docs")
DEFAULT_OUTPUT_DIR = Path("data") / "court_docs_text"
DEFAULT_LOG_PATH = Path("data") / "ocr_extractor.log"
DEFAULT_SUMMARY_CSV = Path("data") / "court_docs_ocr_summary.csv"
DEFAULT_METADATA_JSON = Path("data") / "ocr_metadata.json"
DEFAULT_DPI = 300
LOW_CONF_THRESHOLD = 70  # below this, flag for manual review
MIN_TEXT_LENGTH = 50  # flag very short pages


# ---------------------------------------------------------------------------
# Data structures
# ---------------------------------------------------------------------------

@dataclass
class PageResult:
    page_number: int
    avg_confidence: float
    low_confidence: bool
    text_length: int
    processing_time: float
    error: Optional[str] = None


@dataclass
class DocumentResult:
    pdf_path: Path
    text_output_path: Path
    pages_processed: int
    pages_failed: int
    avg_confidence: float
    low_conf_pages: List[int]
    total_chars: int
    processing_time: float
    quality_score: float
    error: Optional[str] = None


# ---------------------------------------------------------------------------
# OCR helpers
# ---------------------------------------------------------------------------

def setup_logging(log_path: Path, verbose: bool = False) -> None:
    """Configure console + file logging with optional verbose mode."""
    log_path.parent.mkdir(parents=True, exist_ok=True)
    level = logging.DEBUG if verbose else logging.INFO
    file_formatter = logging.Formatter(
        "%(asctime)s [%(levelname)s] %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
    )
    console_formatter = logging.Formatter("%(levelname)s: %(message)s")

    file_handler = logging.FileHandler(log_path, encoding="utf-8")
    file_handler.setLevel(level)
    file_handler.setFormatter(file_formatter)

    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setLevel(level)
    console_handler.setFormatter(console_formatter)

    logger = logging.getLogger()
    logger.setLevel(level)
    logger.handlers.clear()
    logger.addHandler(file_handler)
    logger.addHandler(console_handler)


def calculate_quality_score(
    avg_confidence: float, text_length: int, pages_failed: int, total_pages: int
) -> float:
    """Compute a 0-100 quality score from confidence, text density, and success rate."""
    conf_score = (avg_confidence / 100) * 60
    expected_chars = total_pages * 2000  # rough density baseline
    density_ratio = min(text_length / expected_chars, 1.0) if expected_chars else 0.0
    density_score = density_ratio * 20
    success_rate = ((total_pages - pages_failed) / total_pages) if total_pages else 0
    success_score = success_rate * 20
    return round(conf_score + density_score + success_score, 1)


def ocr_page(image: Image.Image, lang: str) -> Tuple[str, float]:
    """OCR a single page, returning extracted text and average confidence."""
    data = pytesseract.image_to_data(image, lang=lang, output_type=pytesseract.Output.DICT)
    confidences = [int(conf) for conf in data.get("conf", []) if conf not in ("-1", -1)]
    avg_conf = sum(confidences) / len(confidences) if confidences else 0.0
    text = pytesseract.image_to_string(image, lang=lang)
    return text, avg_conf


def preprocess_image(image: Image.Image) -> Image.Image:
    """Light preprocessing to improve OCR; currently grayscale only."""
    if image.mode != "L":
        image = image.convert("L")
    return image


def extract_pdf(
    pdf_path: Path,
    output_dir: Path,
    lang: str,
    dpi: int,
    poppler_path: Optional[str],
    preprocess: bool = True,
) -> DocumentResult:
    """OCR a PDF and save raw text; return summary for logging/reporting."""
    start_time = time.time()
    output_dir.mkdir(parents=True, exist_ok=True)
    text_output_path = output_dir / f"{pdf_path.stem}.txt"

    try:
        images = convert_from_path(
            pdf_path,
            dpi=dpi,
            poppler_path=poppler_path,
        )
    except Exception as exc:  # pragma: no cover - external dependency errors
        logging.error("Failed to convert PDF %s: %s", pdf_path, exc)
        return DocumentResult(
            pdf_path=pdf_path,
            text_output_path=text_output_path,
            pages_processed=0,
            pages_failed=0,
            avg_confidence=0.0,
            low_conf_pages=[],
            total_chars=0,
            processing_time=0.0,
            quality_score=0.0,
            error=str(exc),
        )

    page_results: List[PageResult] = []
    all_text: List[str] = []
    total_chars = 0

    for idx, image in enumerate(tqdm(images, desc=f"OCR {pdf_path.name}", unit="page", leave=False), start=1):
        page_start = time.time()
        try:
            if preprocess:
                image = preprocess_image(image)

            text, avg_conf = ocr_page(image, lang=lang)
            text_len = len(text.strip())
            total_chars += text_len

            low_conf = (
                avg_conf < LOW_CONF_THRESHOLD
                or text_len < MIN_TEXT_LENGTH
                or not text.strip()
            )
            if low_conf:
                reasons = []
                if avg_conf < LOW_CONF_THRESHOLD:
                    reasons.append(f"conf={avg_conf:.1f}")
                if text_len < MIN_TEXT_LENGTH:
                    reasons.append(f"short={text_len}")
                logging.warning("Low quality on %s page %s (%s)", pdf_path.name, idx, ", ".join(reasons))

            page_time = time.time() - page_start
            page_results.append(PageResult(idx, avg_conf, low_conf, text_len, page_time))
            all_text.append(f"\n=== Page {idx} ===\n{text.strip()}\n")
        except Exception as exc:  # pragma: no cover - OCR runtime errors
            logging.error("Error OCR'ing %s page %s: %s", pdf_path.name, idx, exc)
            page_results.append(PageResult(idx, 0.0, True, 0, 0.0, error=str(exc)))

    with text_output_path.open("w", encoding="utf-8") as f:
        f.write("\n".join(all_text))

    processed = sum(1 for p in page_results if p.error is None)
    failed = sum(1 for p in page_results if p.error is not None)
    avg_conf_all = (
        sum(p.avg_confidence for p in page_results if p.error is None) / processed
        if processed
        else 0.0
    )
    low_conf_pages = [p.page_number for p in page_results if p.low_confidence]
    processing_time = time.time() - start_time
    quality_score = calculate_quality_score(avg_conf_all, total_chars, failed, len(images))

    return DocumentResult(
        pdf_path=pdf_path,
        text_output_path=text_output_path,
        pages_processed=processed,
        pages_failed=failed,
        avg_confidence=avg_conf_all,
        low_conf_pages=low_conf_pages,
        total_chars=total_chars,
        processing_time=processing_time,
        quality_score=quality_score,
        error=None if failed == 0 else "See log for page errors",
    )


def find_pdfs(input_dir: Path) -> List[Path]:
    """Return sorted list of PDFs to process."""
    return sorted(input_dir.glob("*.pdf"))


def save_metadata(results: List[DocumentResult], output_path: Path) -> None:
    """Write rich metadata JSON for downstream analysis or dashboards."""
    metadata = {
        "extraction_date": datetime.now().isoformat(),
        "total_documents": len(results),
        "total_pages": sum(r.pages_processed for r in results),
        "total_failures": sum(r.pages_failed for r in results),
        "avg_quality_score": round(
            sum(r.quality_score for r in results) / len(results), 1
        ) if results else 0.0,
        "documents": [
            {
                "pdf_name": r.pdf_path.name,
                "pages": r.pages_processed,
                "confidence": r.avg_confidence,
                "quality_score": r.quality_score,
                "low_conf_pages": r.low_conf_pages,
                "total_chars": r.total_chars,
                "processing_time": round(r.processing_time, 2),
            }
            for r in results
        ],
    }
    output_path.parent.mkdir(parents=True, exist_ok=True)
    with output_path.open("w", encoding="utf-8") as f:
        json.dump(metadata, f, indent=2, ensure_ascii=False)


def print_summary(results: List[DocumentResult]) -> None:
    """Print a concise console summary of OCR quality and counts."""
    total_docs = len(results)
    total_pages = sum(r.pages_processed for r in results)
    total_failed = sum(r.pages_failed for r in results)
    avg_quality = (
        sum(r.quality_score for r in results) / total_docs if total_docs else 0
    )

    print("\n" + "=" * 60)
    print("OCR EXTRACTION SUMMARY")
    print("=" * 60)
    print(f"Documents processed: {total_docs}")
    print(f"Total pages: {total_pages}")
    print(f"Failed pages: {total_failed}")
    print(f"Average quality score: {avg_quality:.1f}/100")

    high_quality = sum(1 for r in results if r.quality_score >= 80)
    medium_quality = sum(1 for r in results if 60 <= r.quality_score < 80)
    low_quality = sum(1 for r in results if r.quality_score < 60)

    print("\nQuality breakdown:")
    print(f"  High (>=80):    {high_quality} documents")
    print(f"  Medium (60-79): {medium_quality} documents")
    print(f"  Low (<60):     {low_quality} documents\n")

    if low_quality:
        print("Manual review suggested:")
        for r in results:
            if r.quality_score < 60:
                print(f"  • {r.pdf_path.name} (score: {r.quality_score:.1f})")
    print("=" * 60 + "\n")


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------

def parse_args(argv: Optional[List[str]] = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="OCR court PDFs into raw text files for downstream parsing.",
        epilog="Example: python ocr_extractor.py --input-dir court_docs --verbose",
    )
    parser.add_argument(
        "--input-dir",
        type=Path,
        default=DEFAULT_INPUT_DIR,
        help=f"Directory containing PDFs (default: {DEFAULT_INPUT_DIR})",
    )
    parser.add_argument(
        "--output-dir",
        type=Path,
        default=DEFAULT_OUTPUT_DIR,
        help=f"Directory for OCR text outputs (default: {DEFAULT_OUTPUT_DIR})",
    )
    parser.add_argument(
        "--lang",
        default="eng",
        help="Language code for Tesseract (default: eng).",
    )
    parser.add_argument(
        "--dpi",
        type=int,
        default=DEFAULT_DPI,
        help=f"DPI for PDF rasterization (default: {DEFAULT_DPI}).",
    )
    parser.add_argument(
        "--poppler-path",
        default=None,
        help="Optional path to poppler binaries if not on PATH.",
    )
    parser.add_argument(
        "--log",
        type=Path,
        default=DEFAULT_LOG_PATH,
        help=f"Log file path (default: {DEFAULT_LOG_PATH}).",
    )
    parser.add_argument(
        "--summary-csv",
        type=Path,
        default=DEFAULT_SUMMARY_CSV,
        help=f"Summary CSV path (default: {DEFAULT_SUMMARY_CSV}).",
    )
    parser.add_argument(
        "--metadata-json",
        type=Path,
        default=DEFAULT_METADATA_JSON,
        help=f"Metadata JSON path (default: {DEFAULT_METADATA_JSON}).",
    )
    parser.add_argument(
        "--tesseract-cmd",
        default=None,
        help="Optional path to the tesseract executable if not on PATH.",
    )
    parser.add_argument(
        "--no-preprocess",
        action="store_true",
        help="Disable image preprocessing (faster but may reduce quality).",
    )
    parser.add_argument(
        "--verbose",
        action="store_true",
        help="Enable verbose logging (DEBUG level).",
    )
    return parser.parse_args(argv)


def main(argv: Optional[List[str]] = None) -> int:
    args = parse_args(argv)

    if not args.poppler_path:
        env_poppler = os.environ.get("POPPLER_PATH")
        if env_poppler:
            args.poppler_path = env_poppler

    if not args.tesseract_cmd:
        env_tess = os.environ.get("TESSERACT_CMD")
        if env_tess:
            args.tesseract_cmd = env_tess

    if args.tesseract_cmd:
        pytesseract.pytesseract.tesseract_cmd = args.tesseract_cmd

    setup_logging(args.log, verbose=args.verbose)
    logging.info("Starting OCR extraction from %s", args.input_dir)

    if not args.input_dir.exists():
        logging.error("Input directory does not exist: %s", args.input_dir)
        return 1

    pdfs = find_pdfs(args.input_dir)
    if not pdfs:
        logging.warning("No PDFs found in %s", args.input_dir)
        return 0

    results: List[DocumentResult] = []
    for pdf_path in tqdm(pdfs, desc="Processing PDFs", unit="file"):
        logging.info("Processing %s", pdf_path.name)
        result = extract_pdf(
            pdf_path=pdf_path,
            output_dir=args.output_dir,
            lang=args.lang,
            dpi=args.dpi,
            poppler_path=args.poppler_path,
            preprocess=not args.no_preprocess,
        )
        results.append(result)
        logging.info(
            "Finished %s: pages=%s, failed=%s, confidence=%.1f, quality=%.1f, time=%.2fs",
            pdf_path.name,
            result.pages_processed,
            result.pages_failed,
            result.avg_confidence,
            result.quality_score,
            result.processing_time,
        )

    summary_fields = [
        "pdf_name",
        "text_output",
        "pages_processed",
        "pages_failed",
        "avg_confidence",
        "quality_score",
        "total_chars",
        "processing_time",
        "low_conf_pages",
        "low_confidence",
    ]
    args.summary_csv.parent.mkdir(parents=True, exist_ok=True)
    with args.summary_csv.open("w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=summary_fields)
        writer.writeheader()
        for r in results:
            writer.writerow(
                {
                    "pdf_name": r.pdf_path.name,
                    "text_output": str(r.text_output_path),
                    "pages_processed": r.pages_processed,
                    "pages_failed": r.pages_failed,
                    "avg_confidence": f"{r.avg_confidence:.1f}",
                    "quality_score": f"{r.quality_score:.1f}",
                    "total_chars": r.total_chars,
                    "processing_time": f"{r.processing_time:.2f}",
                    "low_conf_pages": ";".join(map(str, r.low_conf_pages)),
                    "low_confidence": "yes"
                    if r.low_conf_pages or r.avg_confidence < LOW_CONF_THRESHOLD
                    else "no",
                }
            )

    save_metadata(results, args.metadata_json)
    print_summary(results)
    logging.info("Completed OCR for %s documents. See %s for details.", len(results), args.log)
    return 0


if __name__ == "__main__":
    sys.exit(main())


