"""
services/verification_service.py
----------------------------------
Calls the Grok API (xAI) to verify each claim against search evidence.
Parses the structured JSON response into a VerificationResult.

Input:  Claim + List[SearchResult]
Output: VerificationResult
"""

import json
import re
from typing import List, Optional

from openai import OpenAI  # xAI Grok uses the OpenAI-compatible SDK

import config
from models.schemas import (
    Claim, SearchResult, Verdict, VerificationResult, VerdictStatus
)
from prompts.verifier_prompt import SYSTEM_PROMPT, build_verification_prompt
from utils.logger import get_logger

logger = get_logger(__name__)


class VerificationError(Exception):
    """Raised when Grok verification fails unrecoverably."""
    pass


def _get_client() -> OpenAI:
    """Initialize the xAI/Grok client using OpenAI SDK compatibility."""
    if not config.GROK_API_KEY:
        raise VerificationError("GROK_API_KEY is not configured.")
    return OpenAI(
        api_key=config.GROK_API_KEY,
        base_url=config.GROK_BASE_URL,
    )


def verify_claim(claim: Claim, search_results: List[SearchResult]) -> VerificationResult:
    """
    Verify a single claim against its search evidence using Grok.

    Process:
    1. Extract text snippets from SearchResult objects
    2. Build the verification prompt
    3. Call Grok API
    4. Parse JSON response → Verdict
    5. Return VerificationResult

    Args:
        claim: The Claim object to verify
        search_results: Evidence from Tavily search

    Returns:
        VerificationResult with verdict
    """
    # Extract text content and URLs from search results
    evidence_snippets = [r.content for r in search_results if r.content]
    source_urls = [r.url for r in search_results if r.url]

    if not evidence_snippets:
        return VerificationResult(
            claim=claim,
            search_results=search_results,
            verdict=Verdict(
                status=VerdictStatus.FALSE,
                confidence=0.65,
                reasoning="No credible live web evidence was found to support this claim.",
                corrected_fact=None,
                sources=source_urls,
            ),
        )

    try:
        client = _get_client()

        user_prompt = build_verification_prompt(claim.text, evidence_snippets)

        logger.debug(f"Calling Grok for claim: {claim.text[:60]}...")

        response = client.chat.completions.create(
            model=config.GROK_MODEL,
            max_tokens=config.GROK_MAX_TOKENS,
            temperature=config.GROK_TEMPERATURE,
            messages=[
                {"role": "system", "content": SYSTEM_PROMPT},
                {"role": "user", "content": user_prompt},
            ],
        )

        raw_content = response.choices[0].message.content
        logger.debug(f"Grok raw response: {raw_content[:200]}...")

        verdict = _parse_verdict(raw_content, source_urls)

    except VerificationError:
        raise
    except Exception as e:
        logger.error(f"Grok API call failed: {e}")
        # Graceful degradation: keep the required three-label report shape.
        verdict = Verdict(
            status=VerdictStatus.FALSE,
            confidence=0.0,
            reasoning=f"Verification failed due to API error: {str(e)}",
            corrected_fact=None,
            sources=source_urls,
        )

    return VerificationResult(
        claim=claim,
        search_results=search_results,
        verdict=verdict,
    )


def verify_all_claims(
    claims: List[Claim],
    search_results_map: dict,
) -> List[VerificationResult]:
    """
    Verify all claims sequentially.

    Args:
        claims: List of Claim objects
        search_results_map: Dict of {claim_text: List[SearchResult]}

    Returns:
        List of VerificationResult objects
    """
    results = []

    for i, claim in enumerate(claims):
        logger.info(f"Verifying claim {i+1}/{len(claims)}: {claim.text[:60]}...")
        search_results = search_results_map.get(claim.text, [])
        result = verify_claim(claim, search_results)
        results.append(result)

    return results


def _parse_verdict(raw_content: str, fallback_sources: List[str]) -> Verdict:
    """
    Parse Grok's JSON response into a Verdict object.
    Handles malformed JSON gracefully.

    Args:
        raw_content: Raw string from Grok API
        fallback_sources: URLs to use if Grok doesn't return any

    Returns:
        Verdict object
    """
    # Strip any markdown code fences if model adds them despite instructions
    cleaned = raw_content.strip()
    cleaned = re.sub(r"^```json\s*", "", cleaned)
    cleaned = re.sub(r"\s*```$", "", cleaned)
    cleaned = cleaned.strip()

    try:
        data = json.loads(cleaned)
    except json.JSONDecodeError as e:
        logger.warning(f"JSON parse failed: {e}. Raw: {raw_content[:300]}")
        # Try to extract just the JSON object if there's surrounding text
        json_match = re.search(r"\{.*\}", cleaned, re.DOTALL)
        if json_match:
            try:
                data = json.loads(json_match.group())
            except json.JSONDecodeError:
                return _fallback_verdict("Could not parse AI response.", fallback_sources)
        else:
            return _fallback_verdict("Could not parse AI response.", fallback_sources)

    # Map string status to enum
    status_str = data.get("status", "False")
    try:
        status = VerdictStatus(status_str)
    except ValueError:
        logger.warning(f"Unknown status '{status_str}', defaulting to False")
        status = VerdictStatus.FALSE
    if status == VerdictStatus.UNVERIFIABLE:
        status = VerdictStatus.FALSE

    # Clamp confidence to [0, 1]
    confidence = float(data.get("confidence", 0.5))
    confidence = max(0.0, min(1.0, confidence))

    # Sources: prefer Grok's sources_used, fall back to search URLs
    sources = data.get("sources_used", [])
    if not sources:
        sources = fallback_sources

    return Verdict(
        status=status,
        confidence=confidence,
        reasoning=data.get("reasoning", "No reasoning provided."),
        corrected_fact=data.get("corrected_fact"),
        sources=sources,
    )


def _fallback_verdict(reason: str, sources: List[str]) -> Verdict:
    """Return a safe fallback verdict when parsing fails."""
    return Verdict(
        status=VerdictStatus.FALSE,
        confidence=0.0,
        reasoning=reason,
        corrected_fact=None,
        sources=sources,
    )
