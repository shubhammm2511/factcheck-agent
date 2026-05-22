"""
services/search_service.py
--------------------------
Handles all Tavily API interactions for web search.
Takes a claim string, returns a list of SearchResult objects with evidence.

One claim → one search query → N result snippets
"""

from typing import List

from tavily import TavilyClient

import config
from models.schemas import Claim, SearchResult
from utils.logger import get_logger

logger = get_logger(__name__)


class SearchError(Exception):
    """Raised when Tavily search fails."""
    pass


def _get_client() -> TavilyClient:
    """Lazily initialize the Tavily client."""
    if not config.TAVILY_API_KEY:
        raise SearchError("TAVILY_API_KEY is not configured.")
    return TavilyClient(api_key=config.TAVILY_API_KEY)


def search_claim(claim: Claim) -> List[SearchResult]:
    """
    Search the web for evidence related to a single claim.

    Query construction:
    - Use the claim text directly as the query
    - Tavily handles query optimization internally

    Args:
        claim: A Claim object from claim_service

    Returns:
        List of SearchResult objects (empty list if search fails)
    """
    try:
        client = _get_client()

        # Build a focused search query from the claim
        query = _build_query(claim.text)
        logger.debug(f"Searching: {query[:80]}...")

        response = client.search(
            query=query,
            search_depth=config.TAVILY_SEARCH_DEPTH,
            max_results=config.TAVILY_MAX_RESULTS,
            include_answer=True,      # Tavily's AI answer summary — useful for the verifier
            include_raw_content=False, # Keep response size small
            exclude_domains=config.TAVILY_EXCLUDE_DOMAINS,
        )

        results = []

        for r in response.get("results", []):
            result = SearchResult(
                title=r.get("title", "No title"),
                url=r.get("url", ""),
                content=r.get("content", ""),
                score=float(r.get("score", 0.0)),
            )
            results.append(result)

        # Also include Tavily's AI-generated answer as a pseudo-result if available
        tavily_answer = response.get("answer")
        if tavily_answer:
            results.insert(0, SearchResult(
                title="Tavily AI Summary",
                url="",
                content=tavily_answer,
                score=1.0,
            ))

        logger.debug(f"Got {len(results)} results for claim: {claim.text[:60]}...")
        return results

    except SearchError:
        raise
    except Exception as e:
        logger.error(f"Tavily search failed for claim '{claim.text[:60]}': {e}")
        # Return empty list — verification service will mark as UNVERIFIABLE
        return []


def search_all_claims(claims: List[Claim]) -> dict:
    """
    Search for all claims and return a dict mapping claim text → search results.
    Processes sequentially to stay within Tavily rate limits.

    Args:
        claims: List of Claim objects

    Returns:
        Dict of {claim_text: List[SearchResult]}
    """
    results_map = {}

    for i, claim in enumerate(claims):
        logger.info(f"Searching claim {i+1}/{len(claims)}: {claim.text[:60]}...")
        results_map[claim.text] = search_claim(claim)

    return results_map


def _build_query(claim_text: str) -> str:
    """
    Build an optimized search query from a claim.

    Strategy:
    - Use the claim text directly (Tavily handles NLP)
    - Strip leading/trailing whitespace
    - Limit to 200 chars to avoid overly specific queries

    Args:
        claim_text: Raw claim text

    Returns:
        Query string for Tavily
    """
    # Direct claim text works well for Tavily's semantic search
    query = claim_text.strip()

    # Truncate to reasonable query length
    if len(query) > 200:
        # Try to break at a sentence boundary or significant keyword
        query = query[:200].rsplit(" ", 1)[0]

    return query