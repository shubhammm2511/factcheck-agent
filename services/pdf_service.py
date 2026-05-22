"""
services/pdf_service.py
-----------------------
Handles all PDF I/O: opening, page iteration, text extraction, and cleanup.
The rest of the system never imports PyMuPDF — it only calls this service.

Input:  bytes (uploaded PDF file content)
Output: str (clean extracted text) + page count metadata
"""

import io
from typing import Tuple

import fitz  # PyMuPDF

import config
from utils.logger import get_logger
from utils.text_helpers import clean_pdf_text

logger = get_logger(__name__)


class PDFExtractionError(Exception):
    """Raised when PDF cannot be opened or text cannot be extracted."""
    pass


def extract_text_from_pdf(pdf_bytes: bytes) -> Tuple[str, int]:
    """
    Extract and clean all text from a PDF file.

    Strategy:
    - Use PyMuPDF's "text" mode which preserves reading order better than raw
    - Process page by page to stay within memory limits
    - Clean each page before concatenating
    - Cap at MAX_PDF_PAGES to control costs

    Args:
        pdf_bytes: Raw bytes of the uploaded PDF file

    Returns:
        Tuple of (cleaned_text, page_count)

    Raises:
        PDFExtractionError: If the file is not a valid PDF or is encrypted
    """
    if not pdf_bytes:
        raise PDFExtractionError("Empty file received.")

    # Check file size
    size_mb = len(pdf_bytes) / (1024 * 1024)
    if size_mb > config.MAX_PDF_SIZE_MB:
        raise PDFExtractionError(
            f"File too large: {size_mb:.1f} MB. Maximum allowed: {config.MAX_PDF_SIZE_MB} MB."
        )

    try:
        doc = fitz.open(stream=pdf_bytes, filetype="pdf")
    except Exception as e:
        raise PDFExtractionError(f"Could not open PDF: {str(e)}")

    if doc.is_encrypted:
        raise PDFExtractionError("PDF is password-protected. Please upload an unencrypted file.")

    total_pages = len(doc)
    pages_to_process = min(total_pages, config.MAX_PDF_PAGES)

    logger.info(f"PDF opened: {total_pages} pages total, processing {pages_to_process}")

    page_texts = []

    for page_num in range(pages_to_process):
        page = doc[page_num]

        # Extract text with reading-order sort (better for multi-column layouts)
        raw_text = page.get_text("text", sort=True)

        if not raw_text.strip():
            logger.debug(f"Page {page_num + 1}: empty (possibly image-only page)")
            continue

        cleaned = clean_pdf_text(raw_text)

        if cleaned:
            page_texts.append(cleaned)
            logger.debug(f"Page {page_num + 1}: extracted {len(cleaned)} characters")

    doc.close()

    if not page_texts:
        raise PDFExtractionError(
            "No text could be extracted. The PDF may be image-only (scanned). "
            "OCR support is not included in this version."
        )

    # Join pages with double newline to preserve paragraph structure
    full_text = "\n\n".join(page_texts)

    logger.info(f"PDF extraction complete: {len(full_text)} characters from {len(page_texts)} pages")

    return full_text, total_pages


def get_pdf_metadata(pdf_bytes: bytes) -> dict:
    """
    Extract basic metadata from a PDF for display in the UI.

    Returns:
        Dict with title, author, page_count, file_size_mb
    """
    try:
        doc = fitz.open(stream=pdf_bytes, filetype="pdf")
        metadata = doc.metadata or {}
        page_count = len(doc)
        doc.close()

        return {
            "title": metadata.get("title", "Unknown"),
            "author": metadata.get("author", "Unknown"),
            "page_count": page_count,
            "file_size_mb": round(len(pdf_bytes) / (1024 * 1024), 2),
        }
    except Exception:
        return {
            "title": "Unknown",
            "author": "Unknown",
            "page_count": 0,
            "file_size_mb": round(len(pdf_bytes) / (1024 * 1024), 2),
        }