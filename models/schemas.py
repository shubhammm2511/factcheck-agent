"""
models/schemas.py
-----------------
Single source of truth for all data shapes in the Fact-Check Agent.
Every service imports from here. No raw dicts passed between modules.
"""

from dataclasses import dataclass, field
from typing import List, Optional
from enum import Enum


class VerdictStatus(str, Enum):
    """The three possible verdicts for a claim."""
    VERIFIED = "Verified"
    INACCURATE = "Inaccurate"
    FALSE = "False"
    UNVERIFIABLE = "Unverifiable"  # edge case: claim too vague to search


@dataclass
class Claim:
    """
    A single factual claim extracted from the PDF.
    Includes the raw text plus metadata about what type of claim it is.
    """
    text: str                          # The claim sentence/fragment
    claim_type: str                    # e.g. "statistic", "date", "financial", "technical"
    page_number: Optional[int] = None  # Which PDF page it came from
    extraction_method: str = "regex"   # "regex" | "nlp" | "llm"

    def __post_init__(self):
        self.text = self.text.strip()


@dataclass
class SearchResult:
    """
    Evidence retrieved from Tavily for a single claim.
    One claim can have multiple search results.
    """
    title: str
    url: str
    content: str          # Snippet / relevant excerpt
    score: float = 0.0    # Tavily relevance score (0-1)


@dataclass
class Verdict:
    """
    The final verdict for a claim after Grok analysis.
    This is what gets rendered in the UI.
    """
    status: VerdictStatus
    confidence: float                    # 0.0 – 1.0
    reasoning: str                       # Human-readable explanation
    corrected_fact: Optional[str]        # What the fact actually is (if wrong)
    sources: List[str] = field(default_factory=list)  # Source URLs


@dataclass
class VerificationResult:
    """
    The complete result for one claim: the claim + its search evidence + the verdict.
    This is the unit that gets stored, displayed, and exported.
    """
    claim: Claim
    search_results: List[SearchResult]
    verdict: Verdict

    @property
    def status_emoji(self) -> str:
        """Emoji shorthand for UI rendering."""
        return {
            VerdictStatus.VERIFIED: "✅",
            VerdictStatus.INACCURATE: "⚠️",
            VerdictStatus.FALSE: "❌",
            VerdictStatus.UNVERIFIABLE: "❓",
        }[self.verdict.status]

    @property
    def confidence_pct(self) -> int:
        """Confidence as integer percentage for display."""
        return int(self.verdict.confidence * 100)