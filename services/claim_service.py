"""
services/claim_service.py
--------------------------
Extracts verifiable factual claims from cleaned PDF text.

Strategy: Hybrid approach
1. Regex patterns detect sentences containing numeric/factual signals
2. Sentence tokenization preserves full context around each match
3. Deduplication removes near-identical claims
4. Length filtering removes noise

This avoids NLTK/spaCy dependencies while remaining highly effective
at catching the kinds of claims that appear in marketing documents.
"""

import re
from typing import List, Set

import config
from models.schemas import Claim
from utils.logger import get_logger
from utils.text_helpers import split_into_sentences, truncate_text, normalize_whitespace

logger = get_logger(__name__)


# ─── Regex Patterns for Claim Signals ────────────────────────────────────────
# Each pattern is (name, compiled_regex)
# A sentence matching ANY of these is considered a potential claim.

CLAIM_PATTERNS = [
    # Percentages: "grew by 45%", "87% of users", "12.5 percent"
    ("percentage", re.compile(r"\b\d+\.?\d*\s*%|\b\d+\.?\d*\s*percent\b", re.IGNORECASE)),

    # Dollar/financial figures: "$1.2B", "$500 million", "USD 3 trillion"
    ("financial", re.compile(
        r"\$\s*[\d,]+\.?\d*\s*(billion|million|trillion|thousand|B|M|T|K)?\b"
        r"|\b(USD|EUR|GBP)\s*[\d,]+\.?\d*",
        re.IGNORECASE
    )),

    # Large numbers: "1.2 billion users", "500 million downloads"
    ("large_number", re.compile(
        r"\b\d+\.?\d*\s*(billion|million|trillion|thousand)\b",
        re.IGNORECASE
    )),

    # Years: "in 2019", "by 2025", "since 2020"
    ("year", re.compile(r"\b(in|by|since|as of|through|until)\s+(20\d{2}|19\d{2})\b", re.IGNORECASE)),

    # Specific years as data points: "2023 report", "Q3 2024"
    ("year_reference", re.compile(r"\b(20\d{2}|19\d{2})\b")),

    # Growth claims: "grew by X", "increased X%", "declined X%"
    ("growth", re.compile(
        r"\b(grew|grown|growth|increased|increased by|declined|fell|dropped|rose|surged|"
        r"doubled|tripled|quadrupled)\b",
        re.IGNORECASE
    )),

    # Rankings and superlatives: "largest", "fastest", "#1", "first"
    ("ranking", re.compile(
        r"\b(largest|biggest|smallest|fastest|slowest|first|second|third|leading|"
        r"top\s+\d+|number\s+one|#1|ranked)\b",
        re.IGNORECASE
    )),

    # Market size / valuation: "valued at", "market cap", "market size"
    ("market", re.compile(
        r"\b(market\s+(size|cap|capitalization|share|value)|valued\s+at|worth\s+\$|"
        r"valuation\s+of)\b",
        re.IGNORECASE
    )),

    # User/customer metrics: "X monthly active users", "X customers"
    ("user_metric", re.compile(
        r"\b\d+\.?\d*\s*(million|billion|thousand)?\s*(users|customers|subscribers|"
        r"downloads|installs|monthly active|daily active|MAU|DAU)\b",
        re.IGNORECASE
    )),

    # Technical specs: "X GB", "X TB", "X ms latency", "X% uptime"
    ("technical", re.compile(
        r"\b\d+\.?\d*\s*(GB|TB|MB|PB|ms|GHz|MHz|Mbps|Gbps|uptime|latency)\b",
        re.IGNORECASE
    )),

    # Founded / established dates
    ("founding", re.compile(r"\b(founded|established|launched|created|started)\s+(in\s+)?(20\d{2}|19\d{2})\b", re.IGNORECASE)),
]


def extract_claims(text: str) -> List[Claim]:
    """
    Extract verifiable factual claims from cleaned PDF text.

    Process:
    1. Split text into sentences
    2. Score each sentence against claim patterns
    3. Keep sentences that match at least one pattern
    4. Deduplicate and length-filter
    5. Cap at MAX_CLAIMS_PER_DOC

    Args:
        text: Cleaned PDF text from pdf_service

    Returns:
        List of Claim objects, ordered by document appearance
    """
    if not text:
        logger.warning("Empty text passed to claim extractor")
        return []

    sentences = split_into_sentences(text)
    logger.info(f"Tokenized into {len(sentences)} sentences")

    claims = []
    seen_normalized: Set[str] = set()

    for sentence in sentences:
        # Skip too-short or too-long sentences
        if len(sentence) < config.MIN_CLAIM_LENGTH:
            continue
        if len(sentence) > config.MAX_CLAIM_LENGTH:
            sentence = truncate_text(sentence, config.MAX_CLAIM_LENGTH)

        # Check which patterns match
        matched_types = []
        for pattern_name, pattern in CLAIM_PATTERNS:
            if pattern.search(sentence):
                matched_types.append(pattern_name)

        if not matched_types:
            continue

        # Deduplicate: normalize and check for near-identical claims
        normalized = _normalize_for_dedup(sentence)
        if normalized in seen_normalized:
            continue
        seen_normalized.add(normalized)

        # Determine primary claim type (first match wins for labeling)
        claim_type = matched_types[0]

        claim = Claim(
            text=sentence,
            claim_type=claim_type,
            extraction_method="regex",
        )
        claims.append(claim)

        if len(claims) >= config.MAX_CLAIMS_PER_DOC:
            logger.info(f"Hit MAX_CLAIMS_PER_DOC limit ({config.MAX_CLAIMS_PER_DOC})")
            break

    logger.info(f"Extracted {len(claims)} claims from {len(sentences)} sentences")
    return claims


def _normalize_for_dedup(text: str) -> str:
    """
    Normalize a sentence for deduplication purposes.
    Lowercases, strips punctuation, and collapses whitespace.
    """
    normalized = text.lower()
    normalized = re.sub(r"[^\w\s]", "", normalized)
    normalized = normalize_whitespace(normalized)
    return normalized


def get_claim_type_label(claim_type: str) -> str:
    """Human-readable label for a claim type, used in UI."""
    labels = {
        "percentage": " Statistic",
        "financial": " Financial",
        "large_number": " Numeric",
        "year": " Date/Year",
        "year_reference": " Date/Year",
        "growth": " Growth Claim",
        "ranking": " Ranking",
        "market": " Market Data",
        "user_metric": " User Metric",
        "technical": " Technical Spec",
        "founding": " Company Fact",
    }
    return labels.get(claim_type, "🔍 Factual Claim")