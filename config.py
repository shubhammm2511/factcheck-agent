"""
config.py
---------
Centralized configuration for the Fact-Check Agent.
All environment variables, API settings, and tuneable constants live here.
Services import from this module — never os.getenv() in service files.
"""

import os
from dotenv import load_dotenv

# Load .env file (no-op in production where env vars are set directly)
load_dotenv()


# ─── API Keys ────────────────────────────────────────────────────────────────

import streamlit as st

GROK_API_KEY: str = os.getenv("GROK_API_KEY") or st.secrets.get("GROK_API_KEY", "")
TAVILY_API_KEY: str = os.getenv("TAVILY_API_KEY") or st.secrets.get("TAVILY_API_KEY", "")

# ─── Grok / xAI Settings ─────────────────────────────────────────────────────

GROK_BASE_URL: str = "https://api.x.ai/v1"
GROK_MODEL: str = "grok-3-mini"           # Use grok-3-mini for cost efficiency; swap to grok-3 for higher accuracy
GROK_MAX_TOKENS: int = 1024
GROK_TEMPERATURE: float = 0.1             # Low temperature = more deterministic verdicts


# ─── Tavily Settings ─────────────────────────────────────────────────────────

TAVILY_MAX_RESULTS: int = 3               # Results per claim — 3 is the sweet spot for speed vs. coverage
TAVILY_SEARCH_DEPTH: str = "advanced"     # "basic" | "advanced" — advanced gives better snippets
TAVILY_INCLUDE_DOMAINS: list = []         # Restrict to trusted domains (empty = unrestricted)
TAVILY_EXCLUDE_DOMAINS: list = [          # Block low-quality sources
    "pinterest.com",
    "quora.com",
]


# ─── Claim Extraction Settings ───────────────────────────────────────────────

MAX_CLAIMS_PER_DOC: int = 20              # Cap to avoid runaway API costs on large PDFs
MIN_CLAIM_LENGTH: int = 15                # Characters — filters out noise like "2023" alone
MAX_CLAIM_LENGTH: int = 300              # Characters — truncates overly long sentences


# ─── PDF Processing ──────────────────────────────────────────────────────────

MAX_PDF_PAGES: int = 30                   # Limit pages processed to control cost
MAX_PDF_SIZE_MB: int = 10                 # Reject uploads over this size


# ─── App Settings ─────────────────────────────────────────────────────────────

APP_TITLE: str = "Fact-Check Agent"
APP_SUBTITLE: str = "AI-Powered PDF Claim Verification"
APP_VERSION: str = "1.0.0"


# ─── Validation ───────────────────────────────────────────────────────────────

def validate_config() -> list[str]:
    """
    Check that required API keys are present.
    Returns a list of error messages (empty = all good).
    Call this at app startup to fail fast.
    """
    errors = []
    if not GROK_API_KEY:
        errors.append("GROK_API_KEY is not set. Add it to your .env file.")
    if not TAVILY_API_KEY:
        errors.append("TAVILY_API_KEY is not set. Add it to your .env file.")
    return errors