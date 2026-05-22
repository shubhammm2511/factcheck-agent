"""
utils/text_helpers.py
---------------------
Text cleaning, normalization, and sentence utilities.
Handles the messy reality of PDF-extracted text before it hits claim extraction.
"""

import re
import unicodedata
from typing import List


def clean_pdf_text(raw_text: str) -> str:
    """
    Clean raw text extracted from a PDF.
    Handles: ligatures, hyphenated line-breaks, duplicate spaces,
    unicode noise, and garbled encoding artifacts.

    Args:
        raw_text: Raw string from PyMuPDF

    Returns:
        Cleaned, normalized string ready for claim extraction
    """
    if not raw_text:
        return ""

    text = raw_text

    # 1. Normalize unicode (handles ligatures like ﬁ → fi, ﬂ → fl)
    text = unicodedata.normalize("NFKC", text)

    # 2. Fix hyphenated line-breaks (PDF column layout artifact)
    #    e.g. "mar-\nket" → "market"
    text = re.sub(r"(\w)-\n(\w)", r"\1\2", text)

    # 3. Replace newlines that are mid-sentence with a space
    #    Keep double newlines (paragraph breaks)
    text = re.sub(r"(?<!\n)\n(?!\n)", " ", text)

    # 4. Collapse multiple spaces/tabs into single space
    text = re.sub(r"[ \t]{2,}", " ", text)

    # 5. Remove control characters and zero-width spaces
    text = re.sub(r"[\x00-\x08\x0b\x0c\x0e-\x1f\x7f\u200b\u200c\u200d\ufeff]", "", text)

    # 6. Normalize various dash types to a standard hyphen
    text = text.replace("\u2013", "-").replace("\u2014", " - ")

    # 7. Normalize smart quotes to straight quotes
    text = text.replace("\u2018", "'").replace("\u2019", "'")
    text = text.replace("\u201c", '"').replace("\u201d", '"')

    # 8. Clean up bullet points and list markers that fragment sentences
    text = re.sub(r"^\s*[•·●▪▸◦‣]\s*", "", text, flags=re.MULTILINE)

    # 9. Strip leading/trailing whitespace
    text = text.strip()

    return text


def split_into_sentences(text: str) -> List[str]:
    """
    Split cleaned text into individual sentences.
    Uses a simple but robust regex approach (no NLTK dependency needed).

    Handles:
    - Abbreviations (U.S., e.g., etc.)
    - Numbers with decimals (3.14, $1.2B)
    - Multiple sentence terminators

    Args:
        text: Cleaned paragraph text

    Returns:
        List of sentence strings
    """
    if not text:
        return []

    # Protect known abbreviations and decimal numbers from sentence splitting
    # Temporarily replace them with placeholders
    protected = text

    # Protect "e.g.", "i.e.", "etc.", "vs.", "U.S.", "U.K.", "approx."
    abbreviations = [
        r"(?<=[A-Z])\.(?=[A-Z]\.)",   # U.S.A.
        r"(?<=\bDr)\.",
        r"(?<=\bMr)\.",
        r"(?<=\bMs)\.",
        r"(?<=\bMrs)\.",
        r"(?<=\betc)\.",
        r"(?<=\bvs)\.",
        r"(?<=\bapprox)\.",
        r"(?<=\be\.g)\.",
        r"(?<=\bi\.e)\.",
    ]
    for pattern in abbreviations:
        protected = re.sub(pattern, "<!DOT!>", protected)

    # Protect decimal numbers: "3.14", "$1.2B"
    protected = re.sub(r"(\d)\.(\d)", r"\1<!DOT!>\2", protected)

    # Split on sentence terminators followed by whitespace + capital letter
    sentences = re.split(r"(?<=[.!?])\s+(?=[A-Z\"])", protected)

    # Restore placeholders
    sentences = [s.replace("<!DOT!>", ".").strip() for s in sentences]

    # Filter out empty strings and very short fragments
    sentences = [s for s in sentences if len(s) > 10]

    return sentences


def truncate_text(text: str, max_chars: int = 300) -> str:
    """
    Truncate text to max_chars, breaking at a word boundary.
    Used to keep claims within a reasonable length for the LLM prompt.
    """
    if len(text) <= max_chars:
        return text
    truncated = text[:max_chars]
    # Break at last space to avoid cutting mid-word
    last_space = truncated.rfind(" ")
    if last_space > max_chars * 0.7:  # Only use word boundary if it's not too short
        truncated = truncated[:last_space]
    return truncated + "…"


def normalize_whitespace(text: str) -> str:
    """Collapse all whitespace to single spaces and strip."""
    return re.sub(r"\s+", " ", text).strip()